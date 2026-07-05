"""Percezione NLP: prompt dell'utente -> entità -> triple RDF per l'ontologia.

Trasforma un intento in linguaggio libero ("I want to do intervals for 30
minutes") nel vocabolario dell'ontologia, così la A-Box può essere popolata
e validata dal gate SHACL.

Due backend di estrazione dietro UN'UNICA interfaccia (Rule 3 e 7 del corso):
  - "dictionary": matching rule-based longest-match-first sulle label
    dell'ontologia (la baseline del corso; sempre disponibile, riusa
    `loader.label_dictionary`).
  - "gliner": NER zero-shot (avanzato; `pip install gliner`, import lazy —
    il modulo funziona anche senza).
I numeri con unità (velocità, durata) li estrae una piccola regex: i modelli
NER trovano lo *span* ("5 km/h") ma non interpretano il valore numerico.

Routing (la distinzione qualitativo/quantitativo — un solo if, non due sistemi):
  - prompt quantitativo (velocità/durata dichiarate) -> si usa il target
    dichiarato dall'utente (calcolo "chirurgico" del BPM);
  - prompt qualitativo (solo parole di umore/sforzo)  -> si delega ai sensori
    (il ponte HR -> effort -> target in pipeline.py).

CLI:  python -m algorun.nlp "I want an easy recovery run for 40 minutes"
"""

from __future__ import annotations

import re
import sys

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, XSD

from algorun.ontology.loader import AR, load_ontology, load_shapes

EX = Namespace("http://algorun.org/data#")

# Label per il backend GLiNER, mappate 1:1 sulle classi dell'ontologia.
GLINER_LABELS = ["workout goal", "training phase", "intensity", "music genre"]

# Regex per gli slot quantitativi (valore + unità).
_DURATION_RE = re.compile(r"(\d+)\s*(?:min|minute|minutes|minuti)\b", re.I)
_HOURS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:h|hour|hours|ora|ore)\b", re.I)
_SPEED_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:km/?h|kmh|km/hour|km orari)\b", re.I)


# ---------------------------------------------------------------- estrazione

def dictionary_extract(text: str) -> list[dict]:
    """Baseline: dictionary matching longest-match-first sulle label OWL.

    Scorre il dizionario (già ordinato dalla forma più lunga alla più corta,
    come richiede il corso) e marca i caratteri già "presi" per evitare
    sovrapposizioni. Ritorna entità [{surface, iri, type_iri, start, end}].
    """
    schema = load_ontology()
    lowered = text.lower()
    taken = [False] * len(text)          # caratteri già assegnati a un'entità
    entities: list[dict] = []
    for surface, iri, kind in schema.label_dictionary():   # longest-first
        if kind != "individual":
            continue
        start = lowered.find(surface)
        while start != -1:
            end = start + len(surface)
            if not any(taken[start:end]):
                type_iri = next(schema.graph.objects(iri, RDF.type), None)
                entities.append({"surface": surface, "iri": str(iri),
                                 "type_iri": str(type_iri) if type_iri else None,
                                 "start": start, "end": end})
                for i in range(start, end):
                    taken[i] = True
            start = lowered.find(surface, end)
    entities.sort(key=lambda e: e["start"])
    return entities


def gliner_extract(text: str, threshold: float = 0.4) -> list[dict]:
    """Backend avanzato: GLiNER zero-shot (nessun fine-tuning).

    Import lazy: il modulo funziona anche senza GLiNER installato. Gli span
    trovati vengono "ancorati" agli IRI dell'ontologia cercando la superficie
    nel dizionario delle label (grounding per label).
    """
    from gliner import GLiNER  # pip install gliner

    model = GLiNER.from_pretrained("urchade/gliner_small-v2.1")
    schema = load_ontology()
    label_dict = schema.label_dictionary()          # già longest-match-first
    label_to_iri = {s: iri for s, iri, _ in label_dict}
    out: list[dict] = []
    for ent in model.predict_entities(text, GLINER_LABELS, threshold=threshold):
        surface = ent["text"].lower()
        # grounding: match esatto con la label, altrimenti la label più lunga
        # CONTENUTA nello span (GLiNER trova "easy recovery run", noi ancoriamo
        # "recovery run" -> ar:Easy). Senza questo passo il recall crolla.
        iri = label_to_iri.get(surface)
        if iri is None:
            for s, cand, kind in label_dict:
                if kind == "individual" and s in surface:
                    iri = cand
                    break
        out.append({"surface": ent["text"], "iri": str(iri) if iri else None,
                    "type_iri": None, "start": ent["start"], "end": ent["end"],
                    "gliner_label": ent["label"]})
    return out


def parse_quantities(text: str) -> dict:
    """Regex per gli slot quantitativi. Ritorna {} se il prompt è qualitativo."""
    q: dict = {}
    if (m := _DURATION_RE.search(text)):
        q["duration_min"] = float(m.group(1))
    elif (m := _HOURS_RE.search(text)):
        q["duration_min"] = float(m.group(1)) * 60
    if (m := _SPEED_RE.search(text)):
        q["speed_kmh"] = float(m.group(1))
    return q


# ------------------------------------------------------------------- routing

def classify(quantities: dict) -> str:
    """Il router qualitativo/quantitativo: un solo if, non due sistemi."""
    return "quantitative" if quantities else "qualitative"


# ------------------------------------- quantitativo: target BPM "chirurgico"
# La cadenza cresce con la velocità (155-168 spm a ritmo facile, 170-178 a
# tempo, 176-186 in gara). Regressione lineare calibrata su quei range; poi
# entrainment uditivo-motorio 1:1 (BPM = cadenza) con half-time come ripiego
# (un passo ogni due beat) — Van Dyck et al. (2015).
CADENCE_INTERCEPT = 134.0
CADENCE_SLOPE = 2.9          # spm per ogni km/h in più
CADENCE_MIN, CADENCE_MAX = 150.0, 190.0


def target_cadence_from_speed(speed_kmh: float) -> float:
    """Velocità dichiarata -> cadenza target (passi al minuto)."""
    cadence = CADENCE_INTERCEPT + CADENCE_SLOPE * speed_kmh
    return round(min(max(cadence, CADENCE_MIN), CADENCE_MAX), 1)


def target_bpm(speed_kmh: float) -> dict:
    """Target BPM chirurgico dalla velocità dichiarata: un valore esatto,
    non una banda. 1:1 = cadenza; half_time = cadenza/2 (tracce più calme)."""
    cadence = target_cadence_from_speed(speed_kmh)
    return {"cadence_spm": cadence, "bpm_one_to_one": cadence,
            "bpm_half_time": round(cadence / 2, 1)}


# ----------------------------------------------------------------- grounding

# quale predicato dell'ontologia usare, per ciascuna classe di entità
_PREDICATE = {
    str(AR.WorkoutType): AR.hasWorkoutType,
    str(AR.TrainingPhase): AR.hasPhase,
    str(AR.EffortState): AR.hasEffortState,
}


def ground(text: str, backend: str = "dictionary") -> dict:
    """Wrapper di grounding: prompt -> triple RDF per la A-Box, più routing.

    Ritorna {entities, quantities, mode, bpm_target, graph, shacl_ok}.
    Nota: `speed_kmh` viene interpretata e trasformata in BPM target; il
    *controllo* live della velocità arriverà col sensore GPS (vedi gps.py).
    """
    extract = gliner_extract if backend == "gliner" else dictionary_extract
    entities = extract(text)
    quantities = parse_quantities(text)
    mode = classify(quantities)

    g = Graph()
    g.bind("ar", AR)
    g.add((EX.runner, RDF.type, AR.Runner))
    g.add((EX.session, RDF.type, AR.WorkoutSession))
    g.add((EX.session, AR.performedBy, EX.runner))

    for e in entities:
        pred = _PREDICATE.get(e["type_iri"])
        if pred is not None and e["iri"]:
            g.add((EX.session, pred, AR.term(e["iri"].split("#")[-1])))
    if "duration_min" in quantities:
        g.add((EX.session, AR.durationMinutes,
               Literal(str(quantities["duration_min"]), datatype=XSD.decimal)))

    # Quantitativo + velocità -> BPM chirurgico (esatto, dalla velocità
    # dichiarata). I prompt qualitativi lasciano None e delegano al ponte HR.
    bpm_target = None
    if "speed_kmh" in quantities:
        bpm_target = target_bpm(quantities["speed_kmh"])
        g.add((EX.session, AR.appliedTargetBpm,
               Literal(str(bpm_target["bpm_one_to_one"]), datatype=XSD.decimal)))

    conforms, _, _ = _validate(g)
    return {"entities": entities, "quantities": quantities, "mode": mode,
            "bpm_target": bpm_target, "graph": g, "shacl_ok": conforms}


def _validate(graph: Graph):
    from pyshacl import validate
    return validate(data_graph=graph + load_ontology().graph,
                    shacl_graph=load_shapes(), inference="none")


# ----------------------------------------------------------------- benchmark

def prf1(predicted: set, gold: set) -> dict:
    """Precision / Recall / F1 (metriche del Block 14), su insiemi di IRI."""
    tp = len(predicted & gold)
    precision = tp / len(predicted) if predicted else 0.0
    recall = tp / len(gold) if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def evaluate(cases: list[dict], backend: str = "dictionary") -> dict:
    """P/R/F1 micro-mediate dell'estrazione di entità su prompt annotati.

    `cases` è il gold set: [{"text": ..., "gold_iris": [...]}]. Serve per il
    confronto baseline (dictionary) vs avanzato (gliner) richiesto dal corso.
    """
    tp = fp = fn = 0
    for c in cases:
        pred = {e["iri"] for e in ground(c["text"], backend)["entities"] if e["iri"]}
        gold = set(c["gold_iris"])
        tp += len(pred & gold)
        fp += len(pred - gold)
        fn += len(gold - pred)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": round(precision, 3), "recall": round(recall, 3),
            "f1": round(f1, 3), "tp": tp, "fp": fp, "fn": fn}


# ------------------------------------------------------------------------ CLI

def main() -> None:
    text = " ".join(sys.argv[1:]) or "I want an easy recovery run for 40 minutes"
    r = ground(text)
    print(f'Prompt: "{text}"')
    print(f"Mode:   {r['mode']}  (quantitative = target dichiarato; "
          f"qualitative = delega al sensore HR)")
    print("Entities:")
    for e in r["entities"]:
        print(f"  '{e['surface']}' -> {e['iri']}")
    if r["quantities"]:
        print(f"Quantities: {r['quantities']}")
    if r["bpm_target"]:
        t = r["bpm_target"]
        print(f"Surgical target: cadence {t['cadence_spm']} spm -> "
              f"BPM {t['bpm_one_to_one']} (1:1) o {t['bpm_half_time']} (half-time)")
    print(f"SHACL valid: {r['shacl_ok']}")
    print("Triples:")
    for s, p, o in r["graph"]:
        if p != RDF.type:
            print(f"  {s.split('#')[-1]}  {p.split('#')[-1]}  "
                  f"{str(o).split('#')[-1]}")


if __name__ == "__main__":
    main()
