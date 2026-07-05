"""The bridge: simulated sensor data -> ontology -> SHACL -> acoustic target.

This is the first end-to-end slice of AlgoRun. It shows that the teammate's
physiological analysis (BPM window -> effort state) actually *activates* the
ontology: the effort populates an RDF graph, SHACL validates it, and a SPARQL
query reads the prescribed acoustic target back out of the ontology.

Four small steps (see the plan / the ontology comments for the theory):
  1-2. HRR + effort state         -> done by sensors/physiological_state.py
  3.   effort -> acoustic target  -> read from the ontology via SPARQL
  4.   safety override            -> if HR >= 93% HRmax, force a calm target

Run the demo:  python -m algorun.pipeline
"""

from __future__ import annotations

from pyshacl import validate as shacl_validate
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, XSD

from algorun.ontology.loader import AR, load_ontology, load_shapes
from algorun.sensors.physiological_state import PhysiologicalAnalysis, analyze_bpm_window

EX = Namespace("http://algorun.org/data#")

# Safety line: at or above this fraction of HRmax we force a calm target.
SAFE_MAX_FRACTION = 0.93
# A target is "energetic" (forbidden in the danger zone) above this BPM.
CALM_BPM_CEILING = 140

# The teammate's effort-state strings map 1:1 onto ontology individuals by
# label, so ar[state] is the right IRI (e.g. "LowEffort" -> ar:LowEffort).


def window_to_graph(analysis: PhysiologicalAnalysis, resting_hr: float,
                    max_hr: float, workout_goal: str) -> Graph:
    """Step 1-2 result -> RDF triples the ontology can validate and query."""
    g = Graph()
    g.bind("ar", AR)
    g.bind("ex", EX)

    def dec(v: float) -> Literal:
        return Literal(str(v), datatype=XSD.decimal)

    safe_max = round(max_hr * SAFE_MAX_FRACTION, 1)

    g.add((EX.runner, RDF.type, AR.Runner))
    g.add((EX.runner, AR.maxHeartRateBpm, dec(max_hr)))
    g.add((EX.runner, AR.restingHeartRateBpm, dec(resting_hr)))
    g.add((EX.runner, AR.safeMaxHeartRateBpm, dec(safe_max)))

    g.add((EX.session, RDF.type, AR.WorkoutSession))
    g.add((EX.session, AR.performedBy, EX.runner))
    g.add((EX.session, AR.hasWorkoutType, AR[workout_goal.capitalize()]))
    g.add((EX.session, AR.hasEffortState, AR[analysis.effort_state]))
    g.add((EX.session, AR.hasTrend, AR[analysis.trend_state]))
    g.add((EX.session, AR.currentHeartRateBpm, dec(round(analysis.current_bpm, 1))))
    return g


def validate(graph: Graph) -> tuple[bool, str]:
    """Step: the SHACL gate. Ontology merged in, inference OFF (closed world)."""
    merged = graph + load_ontology().graph
    conforms, _, report = shacl_validate(
        data_graph=merged, shacl_graph=load_shapes(), inference="none")
    return conforms, report


_TARGET_QUERY = """
PREFIX ar: <http://algorun.org/ontology#>
SELECT ?bpmMin ?bpmMax ?enMin ?enMax WHERE {
    ?effort ar:prescribesTarget ?t .
    ?t ar:targetBpmMin ?bpmMin ; ar:targetBpmMax ?bpmMax ;
       ar:targetEnergyMin ?enMin ; ar:targetEnergyMax ?enMax .
}"""


def acoustic_target(effort_state: str) -> dict:
    """Step 3: ask the ontology (SPARQL) which target this effort prescribes."""
    g = load_ontology().graph
    rows = list(g.query(_TARGET_QUERY,
                        initBindings={"effort": AR[effort_state]}))
    r = rows[0]
    return {"bpm_min": float(r[0]), "bpm_max": float(r[1]),
            "energy_min": float(r[2]), "energy_max": float(r[3])}


def decide(analysis: PhysiologicalAnalysis, resting_hr: float, max_hr: float,
           workout_goal: str) -> dict:
    """Put it together: graph -> SHACL -> target -> step 4 safety override."""
    graph = window_to_graph(analysis, resting_hr, max_hr, workout_goal)
    shacl_ok, report = validate(graph)

    target = acoustic_target(analysis.effort_state)

    # Step 4: safety override. Above the safe-max line, force a calm target
    # regardless of the effort state (Terry & Karageorghis 2011).
    forced = False
    if analysis.current_bpm >= max_hr * SAFE_MAX_FRACTION and target["bpm_max"] > CALM_BPM_CEILING:
        target = acoustic_target("LowEffort")
        forced = True

    return {"hr": round(analysis.current_bpm, 1), "hrr": round(analysis.current_hrr, 2),
            "effort": analysis.effort_state, "shacl_ok": shacl_ok,
            "target": target, "forced_recovery": forced, "shacl_report": report}


def _demo_window(bpm_level: float, resting_hr: float, max_hr: float):
    """Build a rising 10 s BPM window centred on bpm_level (in-memory)."""
    values = [bpm_level - 3 + i for i in range(10)]  # gentle upward ramp
    analysis = analyze_bpm_window(values, resting_hr=resting_hr, max_hr=max_hr)
    return analysis


def main() -> None:
    resting_hr, max_hr = 60.0, 195.0
    print(f"Runner: rest={resting_hr:.0f} max={max_hr:.0f} "
          f"safe_max={max_hr * SAFE_MAX_FRACTION:.0f} bpm\n")
    header = f"{'HR':>5} {'HRR':>5} {'effort':>15} {'SHACL':>6} {'target BPM':>12} {'note':>10}"
    print(header)
    print("-" * len(header))
    for bpm in (100, 135, 165, 185):
        d = decide(_demo_window(bpm, resting_hr, max_hr), resting_hr, max_hr, "interval")
        band = f"{d['target']['bpm_min']:.0f}-{d['target']['bpm_max']:.0f}"
        note = "FORCED calm" if d["forced_recovery"] else ""
        ok = "ok" if d["shacl_ok"] else "FAIL"
        print(f"{d['hr']:>5.0f} {d['hrr']:>5.2f} {d['effort']:>15} {ok:>6} {band:>12} {note:>10}")


if __name__ == "__main__":
    main()
