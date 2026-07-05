"""M1 tests — ontology integrity and label dictionary construction."""

from rdflib import URIRef

from algorun.ontology.loader import AR, load_ontology


def test_ontology_parses_and_has_core_classes():
    schema = load_ontology()
    for cls in (
        AR.Runner,
        AR.WorkoutSession,
        AR.WorkoutType,
        AR.TrainingPhase,
        AR.HeartRateReading,
        AR.EffortState,
        AR.Song,
        AR.Playlist,
    ):
        assert cls in schema.classes, f"missing class {cls}"


def test_every_object_property_declares_domain_and_range():
    """GUIDELINES.md Rule 1: every relation MUST have explicit domain/range."""
    schema = load_ontology()
    assert schema.object_properties, "no object properties found"
    for spec in schema.object_properties.values():
        assert spec.domain is not None, f"{spec.iri} has no rdfs:domain"
        assert spec.range is not None, f"{spec.iri} has no rdfs:range"


def test_workout_type_and_phase_individuals_present():
    schema = load_ontology()
    for ind in (AR.Easy, AR.Moderate, AR.Interval,
                AR.WarmUp, AR.Steady, AR.Hard, AR.Recovery,
                AR.LowEffort, AR.TargetEffort, AR.HighEffort, AR.VeryHighEffort,
                AR.Increasing, AR.Stable, AR.Decreasing):
        assert ind in schema.individuals, f"missing individual {ind}"


def test_label_dictionary_is_longest_match_first():
    """Course mechanic for the classical rule-based detector."""
    schema = load_ontology()
    entries = schema.label_dictionary()
    lengths = [len(form) for form, _, _ in entries]
    assert lengths == sorted(lengths, reverse=True)
    forms = {form for form, _, _ in entries}
    # synonyms from skos:altLabel must be present (implicit-tier support)
    assert "heart rate" in forms
    assert "hiit" in forms
    assert "track" in forms


def test_relation_dictionary_contains_triggers():
    schema = load_ontology()
    triggers = {form for form, _ in schema.relation_dictionary()}
    assert "performs" in triggers
    assert "records" in triggers
    assert "suits" in triggers


def test_surface_forms_map_back_to_expected_iri():
    schema = load_ontology()
    mapping = {form: iri for form, iri, _ in schema.label_dictionary()}
    assert mapping["hr"] == URIRef(str(AR.HeartRateReading))
    assert mapping["intervals"] == URIRef(str(AR.Interval))
