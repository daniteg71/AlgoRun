"""M1-bis tests — v0.2: disjoint cores, full inverses, effort→target."""

from rdflib.namespace import OWL, RDF

from algorun.ontology.loader import AR, load_ontology


def test_three_cores_declared_disjoint():
    g = load_ontology().graph
    cores = {AR.Agent, AR.Process, AR.InformationEntity}
    disjoint = set(g.subject_objects(OWL.disjointWith))
    pairs = {frozenset(p) for p in disjoint}
    assert frozenset({AR.Agent, AR.Process}) in pairs
    assert frozenset({AR.Agent, AR.InformationEntity}) in pairs
    assert frozenset({AR.Process, AR.InformationEntity}) in pairs


def test_every_object_property_has_an_inverse():
    """v0.2 goal: full forward/inverse coverage (Block 12)."""
    g = load_ontology().graph
    with_inverse = set(g.subjects(OWL.inverseOf, None)) | set(
        g.objects(None, OWL.inverseOf))
    for prop in g.subjects(RDF.type, OWL.ObjectProperty):
        assert prop in with_inverse, f"{prop} has no inverse"


def test_new_prefers_genre_property_present():
    schema = load_ontology()
    assert AR.prefersGenre in schema.object_properties
    spec = schema.object_properties[AR.prefersGenre]
    assert spec.domain == AR.Runner and spec.range == AR.Genre


def test_effort_states_prescribe_targets():
    g = load_ontology().graph
    for effort in (AR.LowEffort, AR.TargetEffort, AR.HighEffort, AR.VeryHighEffort):
        assert list(g.objects(effort, AR.prescribesTarget)), f"{effort} has no target"
