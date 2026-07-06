"""Percezione NLP: prompt dell'utente -> entità -> triple RDF per l'ontologia.

Trasforma un intento in linguaggio libero ("I want to do intervals for 30
minutes") nel vocabolario dell'ontologia, così la A-Box può essere popolata
e validata dal gate SHACL.

Estrazione baseline (rule-based longest-match-first sulle label OWL, riusa
`loader.label_dictionary`). I numeri con unità (velocità, durata) li estrae
una piccola regex. Modelli NLP piu' pesanti (Joint intent+slot, ecc.) vivono
solo nel benchmark (`benchmarks/`), non qui.

Routing qualitativo/quantitativo (un solo if, non due sistemi):
  - prompt quantitativo (velocità/durata dichiarate) -> target BPM dichiarato
    (calcolo "chirurgico");
  - prompt qualitativo (solo parole di umore/sforzo) -> nessun BPM esatto, il
    ramo qualitativo dello scorer lavora su energia/valenza.

CLI:  python -m algorun.nlp "I want an easy recovery run for 40 minutes"
"""

from __future__ import annotations

import re
import sys

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, XSD

from algorun.ontology.loader import AR, load_ontology, load_shapes

EX = Namespace("http://algorun.org/data#")

# Regex per gli slot quantitativi (valore + unità).
_DURATION_RE = re.compile(r"(\d+)\s*(?:min|minute|minutes|minuti)\b", re.I)
_HOURS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:h|hour|hours|ora|ore)\b", re.I)
_SPEED_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:km/?h|kmh|km/hour|km orari)\b", re.I)


# ---------------------------------------------------------------- estrazione

def dictionary_extract(text: str) -> list[dict]:
    """Estrazione entità: dictionary matching longest-match-first sulle label OWL.

    Scorre il dizionario (già ordinato dalla forma più lunga alla più corta)
    e marca i caratteri già "presi" per evitare sovrapposizioni.
    Ritorna entità [{surface, iri, type_iri, start, end}].
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


def ground(text: str) -> dict:
    """Wrapper di grounding: prompt -> triple RDF per la A-Box, più routing.

    Ritorna {entities, quantities, mode, bpm_target, graph, shacl_ok}.
    """
    entities = dictionary_extract(text)
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
    # dichiarata). I prompt qualitativi lasciano None: il ramo qualitativo
    # dello scorer lavora su energia/valenza, non su un BPM esatto.
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


def evaluate(cases: list[dict]) -> dict:
    """P/R/F1 micro-mediate dell'estrazione di entità su prompt annotati.

    `cases` è il gold set: [{"text": ..., "gold_iris": [...]}].
    """
    tp = fp = fn = 0
    for c in cases:
        pred = {e["iri"] for e in ground(c["text"])["entities"] if e["iri"]}
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
          f"qualitative = ramo energia/valenza)")
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
