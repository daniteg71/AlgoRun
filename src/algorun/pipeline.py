"""Il ponte: dati simulati del sensore -> ontologia -> SHACL -> target acustico.

È la prima fetta end-to-end di AlgoRun. Dimostra che l'analisi fisiologica del
socio (finestra BPM -> effort state) *attiva* davvero l'ontologia: l'effort
popola un grafo RDF, SHACL lo valida, e una query SPARQL legge dall'ontologia
il target acustico prescritto.

Quattro passi piccoli (la teoria è nei commenti dell'ontologia):
  1-2. HRR + effort state          -> già fatti da sensors/physiological_state.py
  3.   effort -> target acustico   -> letto dall'ontologia via SPARQL
  4.   override di sicurezza       -> se HR >= 93% HRmax, forza un target calmo

Demo:  python -m algorun.pipeline
"""

from __future__ import annotations

from pyshacl import validate as shacl_validate
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, XSD

from algorun.ontology.loader import AR, load_ontology, load_shapes
from algorun.sensors.physiological_state import PhysiologicalAnalysis, analyze_bpm_window

EX = Namespace("http://algorun.org/data#")

# Linea di sicurezza: a/oltre questa frazione di HRmax si forza un target calmo.
SAFE_MAX_FRACTION = 0.93
# Un target è "energico" (vietato in zona pericolo) sopra questo BPM.
CALM_BPM_CEILING = 140

# Le stringhe di effort del socio mappano 1:1 sugli individui dell'ontologia
# per label: ar[stato] è l'IRI giusto (es. "LowEffort" -> ar:LowEffort).


def window_to_graph(analysis: PhysiologicalAnalysis, resting_hr: float,
                    max_hr: float, workout_goal: str) -> Graph:
    """Risultato dei passi 1-2 -> triple RDF che l'ontologia valida e interroga."""
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
    """Il gate SHACL: ontologia fusa nei dati, inferenza SPENTA (closed world).

    Con l'inferenza accesa le violazioni di dominio verrebbero "classificate"
    invece che respinte — per questo il corso impone SHACL come constraint gate.
    """
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
    """Passo 3: chiede all'ontologia (SPARQL) quale target prescrive l'effort.

    La conoscenza sta nell'ontologia (prescribesTarget); il codice la legge.
    """
    g = load_ontology().graph
    rows = list(g.query(_TARGET_QUERY,
                        initBindings={"effort": AR[effort_state]}))
    r = rows[0]
    return {"bpm_min": float(r[0]), "bpm_max": float(r[1]),
            "energy_min": float(r[2]), "energy_max": float(r[3])}


def decide(analysis: PhysiologicalAnalysis, resting_hr: float, max_hr: float,
           workout_goal: str) -> dict:
    """Orchestrazione: grafo -> SHACL -> target -> passo 4 (override sicurezza)."""
    graph = window_to_graph(analysis, resting_hr, max_hr, workout_goal)
    shacl_ok, report = validate(graph)

    target = acoustic_target(analysis.effort_state)

    # Passo 4: override di sicurezza. Oltre la linea safe-max si forza un
    # target calmo qualunque sia l'effort (Terry & Karageorghis 2011: la
    # musica veloce alza HR e arousal — qui serve l'opposto).
    forced = False
    if analysis.current_bpm >= max_hr * SAFE_MAX_FRACTION and target["bpm_max"] > CALM_BPM_CEILING:
        target = acoustic_target("LowEffort")
        forced = True

    return {"hr": round(analysis.current_bpm, 1), "hrr": round(analysis.current_hrr, 2),
            "effort": analysis.effort_state, "shacl_ok": shacl_ok,
            "target": target, "forced_recovery": forced, "shacl_report": report}


def _demo_window(bpm_level: float, resting_hr: float, max_hr: float):
    """Costruisce una finestra BPM di 10 s in leggera salita (in memoria)."""
    values = [bpm_level - 3 + i for i in range(10)]  # rampa dolce verso l'alto
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
