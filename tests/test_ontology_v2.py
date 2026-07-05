"""M1-bis tests — v0.2 additions: disjoint cores, full inverses, reasoner."""

import pytest
from rdflib import Graph, Namespace
from rdflib.namespace import OWL, RDF

from algorun.ontology.evaluation import check_consistency, sample_kg
from algorun.ontology.loader import AR, load_ontology

EX = Namespace("http://algorun.org/data#")


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


def test_ontology_alone_is_consistent():
    assert check_consistency() is True


def test_valid_abox_is_consistent():
    assert check_consistency(sample_kg()) is True


def test_individual_in_two_disjoint_cores_is_inconsistent():
    """The disjointness axioms must actually bite."""
    bad = Graph()
    bad.add((EX.weird, RDF.type, AR.Runner))          # ⊑ Agent
    bad.add((EX.weird, RDF.type, AR.WorkoutSession))  # ⊑ Process
    assert check_consistency(bad) is False
