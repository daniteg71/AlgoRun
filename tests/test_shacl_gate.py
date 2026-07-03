"""M1 tests — the SHACL Constraint Gate rejects invalid triples.

Reproduces the course's canonical example (Block 14, Phase 1): a relation
whose domain is strictly constrained must reject a subject of the wrong
class — no triple enters the Knowledge Graph without passing this gate.
"""

from pyshacl import validate
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, XSD

from algorun.ontology.loader import AR, load_ontology, load_shapes

EX = Namespace("http://algorun.org/data#")


def _validate(data: Graph) -> tuple[bool, str]:
    # NOTE: inference must stay OFF. With RDFS inference, rdfs:domain/range
    # axioms *classify* subjects into the expected class instead of flagging
    # them (open-world semantics), silently legalising every violation. This
    # is precisely why the course mandates SHACL as the constraint gate.
    # The ontology is merged into the data graph by hand (pyshacl only uses
    # ont_graph when inference is enabled) so sh:class can still see
    # individual typings and walk the rdfs:subClassOf hierarchy.
    merged = data + load_ontology().graph
    shapes = load_shapes()
    conforms, _, report_text = validate(
        data_graph=merged,
        shacl_graph=shapes,
        inference="none",
    )
    return conforms, report_text


def test_valid_triples_pass_the_gate():
    data = Graph()
    data.add((EX.danny, RDF.type, AR.Runner))
    data.add((EX.session1, RDF.type, AR.WorkoutSession))
    data.add((EX.danny, AR.performsSession, EX.session1))
    data.add((EX.session1, AR.hasWorkoutType, AR.Interval))
    data.add((EX.hr1, RDF.type, AR.HeartRateReading))
    data.add((EX.session1, AR.recordsReading, EX.hr1))
    data.add((EX.hr1, AR.readingInZone, AR.Z4))
    data.add((EX.hr1, AR.heartRateBpm, Literal("172", datatype=XSD.decimal)))

    conforms, report = _validate(data)
    assert conforms, report


def test_domain_violation_is_rejected():
    """A Playlist cannot perform a session (performsSession domain = Runner)."""
    data = Graph()
    data.add((EX.playlist1, RDF.type, AR.Playlist))
    data.add((EX.session1, RDF.type, AR.WorkoutSession))
    data.add((EX.playlist1, AR.performsSession, EX.session1))

    conforms, report = _validate(data)
    assert not conforms
    assert "performsSession" in report


def test_range_violation_is_rejected():
    """readingInZone must point to an IntensityZone, not a Genre."""
    data = Graph()
    data.add((EX.hr1, RDF.type, AR.HeartRateReading))
    data.add((EX.rock, RDF.type, AR.Genre))
    data.add((EX.hr1, AR.readingInZone, EX.rock))

    conforms, _ = _validate(data)
    assert not conforms


def test_out_of_range_heart_rate_is_rejected():
    data = Graph()
    data.add((EX.hr1, RDF.type, AR.HeartRateReading))
    data.add((EX.hr1, AR.heartRateBpm, Literal("500", datatype=XSD.decimal)))

    conforms, _ = _validate(data)
    assert not conforms
