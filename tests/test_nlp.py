"""Test dell'estrattore entità del refinery (dictionary NER sulle label OWL)."""
from algorun.nlp import dictionary_extract
from algorun.ontology.loader import AR


def test_dictionary_extraction_finds_goal():
    ents = {e["iri"] for e in dictionary_extract("I want to do intervals")}
    assert str(AR.Interval) in ents


def test_extraction_returns_spans_in_order():
    ents = dictionary_extract("warmup then steady")
    starts = [e["start"] for e in ents]
    assert starts == sorted(starts)


def test_no_overlapping_entities():
    ents = dictionary_extract("easy recovery run")
    for a, b in zip(ents, ents[1:]):
        assert a["end"] <= b["start"]
