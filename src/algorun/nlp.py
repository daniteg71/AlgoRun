"""NLP perception: user prompt -> entities -> RDF triples for the ontology.

Turns a free-text intent ("I want to do intervals for 30 minutes") into the
ontology's vocabulary, so the A-Box can be populated and validated.

Two extraction backends behind ONE interface (course Rule 3 & 7):
  - "dictionary": rule-based longest-match over the ontology labels (the course
    baseline; always available, reuses `loader.label_dictionary`).
  - "gliner": zero-shot NER (advanced; `pip install gliner`, lazy-loaded).
Numbers/units (speed, duration) are pulled by a small regex — NER models find
the span but do not parse the value.

Routing (the qualitative/quantitative distinction):
  - quantitative prompt (a speed/duration is stated) -> use the declared target;
  - qualitative prompt (only mood/effort words)      -> defer to the sensors
    (the HR -> effort -> target bridge in pipeline.py).

CLI:  python -m algorun.nlp "I want an easy recovery run for 40 minutes"
"""

from __future__ import annotations

import re
import sys

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, XSD

from algorun.ontology.loader import AR, load_ontology, load_shapes

EX = Namespace("http://algorun.org/data#")

# Labels for the GLiNER backend, mapped 1:1 onto ontology classes.
GLINER_LABELS = ["workout goal", "training phase", "intensity", "music genre"]

# Regex for the quantitative slots (value + unit).
_DURATION_RE = re.compile(r"(\d+)\s*(?:min|minute|minutes|minuti)\b", re.I)
_HOURS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:h|hour|hours|ora|ore)\b", re.I)
_SPEED_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:km/?h|kmh|km/hour|km orari)\b", re.I)


# ---------------------------------------------------------------- extraction

def dictionary_extract(text: str) -> list[dict]:
    """Baseline: longest-match-first dictionary matching over ontology labels.

    Returns entities [{surface, iri, type_iri, start, end}] without overlaps.
    """
    schema = load_ontology()
    lowered = text.lower()
    taken = [False] * len(text)
    entities: list[dict] = []
    for surface, iri, kind in schema.label_dictionary():   # already longest-first
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
    """Advanced backend: zero-shot GLiNER. Lazy import so the module works
    without it installed. Spans are grounded back to ontology IRIs by label."""
    from gliner import GLiNER  # pip install gliner

    model = GLiNER.from_pretrained("urchade/gliner_small-v2.1")
    schema = load_ontology()
    label_to_iri = {s: iri for s, iri, _ in schema.label_dictionary()}
    out: list[dict] = []
    for ent in model.predict_entities(text, GLINER_LABELS, threshold=threshold):
        surface = ent["text"].lower()
        iri = label_to_iri.get(surface)
        out.append({"surface": ent["text"], "iri": str(iri) if iri else None,
                    "type_iri": None, "start": ent["start"], "end": ent["end"],
                    "gliner_label": ent["label"]})
    return out


def parse_quantities(text: str) -> dict:
    """Regex for the quantitative slots. Returns {} when the prompt is qualitative."""
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
    """The qual/quant router: one if, not two systems."""
    return "quantitative" if quantities else "qualitative"


# ------------------------------------------- quantitative: surgical BPM target
# Cadence rises with pace (155-168 easy, 170-178 tempo, 176-186 race). Simple
# linear regression calibrated on those ranges; then 1:1 auditory-motor
# entrainment (BPM = cadence) with half-time as fallback (Van Dyck et al. 2015).
CADENCE_INTERCEPT = 134.0
CADENCE_SLOPE = 2.9          # spm per km/h
CADENCE_MIN, CADENCE_MAX = 150.0, 190.0


def target_cadence_from_speed(speed_kmh: float) -> float:
    """Declared running speed -> target cadence (steps per minute)."""
    cadence = CADENCE_INTERCEPT + CADENCE_SLOPE * speed_kmh
    return round(min(max(cadence, CADENCE_MIN), CADENCE_MAX), 1)


def target_bpm(speed_kmh: float) -> dict:
    """Surgical BPM target from a declared speed: exact value, not a band.
    1:1 = cadence; half_time = cadence/2 (for calmer tracks / easier catalog)."""
    cadence = target_cadence_from_speed(speed_kmh)
    return {"cadence_spm": cadence, "bpm_one_to_one": cadence,
            "bpm_half_time": round(cadence / 2, 1)}


# ------------------------------------------------------------------ grounding

# which ontology predicate to use, per entity class
_PREDICATE = {
    str(AR.WorkoutType): AR.hasWorkoutType,
    str(AR.TrainingPhase): AR.hasPhase,
    str(AR.EffortState): AR.hasEffortState,
}


def ground(text: str, backend: str = "dictionary") -> dict:
    """Wrapper of grounding: prompt -> RDF triples for the A-Box, plus routing.

    Returns {entities, quantities, mode, graph, shacl_ok}. `speed_kmh` is parsed
    but not yet grounded (needs the GPS sensor); it is reported for later.
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

    # Quantitative + speed -> surgical BPM target (exact, from the declared
    # speed). Qualitative prompts leave this None and defer to the HR bridge.
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
    """Precision / Recall / F1 (course Block 14 metrics), set-based on IRIs."""
    tp = len(predicted & gold)
    precision = tp / len(predicted) if predicted else 0.0
    recall = tp / len(gold) if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def evaluate(cases: list[dict], backend: str = "dictionary") -> dict:
    """Micro-averaged P/R/F1 of entity extraction over annotated prompts."""
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
    print(f"Mode:   {r['mode']}  (quantitative = declared target; "
          f"qualitative = defer to HR sensor)")
    print("Entities:")
    for e in r["entities"]:
        print(f"  '{e['surface']}' -> {e['iri']}")
    if r["quantities"]:
        print(f"Quantities: {r['quantities']}")
    if r["bpm_target"]:
        t = r["bpm_target"]
        print(f"Surgical target: cadence {t['cadence_spm']} spm -> "
              f"BPM {t['bpm_one_to_one']} (1:1) or {t['bpm_half_time']} (half-time)")
    print(f"SHACL valid: {r['shacl_ok']}")
    print("Triples:")
    for s, p, o in r["graph"]:
        if p != RDF.type:
            print(f"  {s.split('#')[-1]}  {p.split('#')[-1]}  "
                  f"{str(o).split('#')[-1]}")


if __name__ == "__main__":
    main()
