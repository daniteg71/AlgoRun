"""v0.3 tests — the life-saving SHACL constraints.

These prove the ontology, not the Python controller, is what enforces safety
(course Architecture 4: a symbolic validator governs the AI system).
"""

from pyshacl import validate
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, XSD

from algorun.ontology.loader import AR, load_ontology, load_shapes

EX = Namespace("http://algorun.org/data#")


def _validate(data: Graph) -> tuple[bool, str]:
    merged = data + load_ontology().graph
    conforms, _, text = validate(data_graph=merged, shacl_graph=load_shapes(),
                                 inference="none")
    return conforms, text


def _dec(v):
    return Literal(str(v), datatype=XSD.decimal)


def _session(**stamps) -> Graph:
    g = Graph()
    g.add((EX.danny, RDF.type, AR.Runner))
    g.add((EX.danny, AR.safeMaxHeartRateBpm, _dec(180)))
    g.add((EX.s, RDF.type, AR.WorkoutSession))
    g.add((EX.s, AR.performedBy, EX.danny))
    for prop, val in stamps.items():
        g.add((EX.s, AR[prop], _dec(val)))
    return g


def test_safe_cadence_step_passes():
    # 170 bpm target vs 165 spm cadence → +3%, within 5%
    g = _session(currentCadenceSpm=165, appliedTargetBpm=170)
    conforms, _ = _validate(g)
    assert conforms


def test_cadence_jump_over_5_percent_is_rejected():
    # classic case: running at 140 spm, system tries a 180 bpm track
    g = _session(currentCadenceSpm=140, appliedTargetBpm=180)
    conforms, report = _validate(g)
    assert not conforms
    assert "cadence" in report.lower()


def test_energetic_target_above_safe_hr_is_rejected():
    g = _session(currentHeartRateBpm=185, appliedTargetBpm=175)
    conforms, report = _validate(g)
    assert not conforms
    assert "heart rate" in report.lower()


def test_relaxing_target_above_safe_hr_passes():
    # HR critical but the system correctly chose a calming target (≤140)
    g = _session(currentHeartRateBpm=185, appliedTargetBpm=130)
    conforms, _ = _validate(g)
    assert conforms


def test_emergency_priority_forbids_energetic_target():
    g = _session(appliedTargetBpm=178)
    g.add((EX.s, AR.hasActionPriority, AR.EmergencyPriority))
    conforms, report = _validate(g)
    assert not conforms
    assert "emergency" in report.lower()


def test_emergency_priority_allows_relaxing_target():
    g = _session(appliedTargetBpm=125)
    g.add((EX.s, AR.hasActionPriority, AR.EmergencyPriority))
    conforms, _ = _validate(g)
    assert conforms
