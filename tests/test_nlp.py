"""NLP tests: extraction, quantitative routing, surgical BPM, and P/R/F1.

The GOLD set below is the small annotated benchmark of user prompts (course
Block 14 metrics). Extend it freely — it is the ground truth for evaluation.
"""

from algorun.nlp import (evaluate, ground, parse_quantities, prf1,
                         target_bpm, target_cadence_from_speed)
from algorun.ontology.loader import AR

# Annotated prompts: text -> gold entity IRIs (+ optional quantities).
GOLD = [
    {"text": "I want to do intervals for 30 minutes",
     "gold_iris": [str(AR.Interval)], "duration_min": 30.0},
    {"text": "easy recovery run",
     "gold_iris": [str(AR.Easy)]},
    {"text": "a tempo run at 12 km/h",
     "gold_iris": [str(AR.Moderate)], "speed_kmh": 12.0},
    {"text": "let's push with some hard intervals",
     "gold_iris": [str(AR.Interval), str(AR.Hard)]},
    {"text": "warmup then steady for 20 minutes",
     "gold_iris": [str(AR.WarmUp), str(AR.Steady)], "duration_min": 20.0},
    {"text": "I feel tired, something relaxed",
     "gold_iris": []},
    {"text": "moderate threshold session",
     "gold_iris": [str(AR.Moderate)]},
    {"text": "long endurance run at 10 km/h",
     "gold_iris": [str(AR.Easy)], "speed_kmh": 10.0},
]


def test_dictionary_extraction_finds_goal():
    ents = {e["iri"] for e in ground("I want to do intervals")["entities"]}
    assert str(AR.Interval) in ents


def test_quantities_regex():
    assert parse_quantities("run for 30 minutes")["duration_min"] == 30.0
    assert parse_quantities("go at 12 km/h")["speed_kmh"] == 12.0
    assert parse_quantities("for 1 hour")["duration_min"] == 60.0
    assert parse_quantities("just an easy jog") == {}


def test_routing_qualitative_vs_quantitative():
    assert ground("easy recovery run")["mode"] == "qualitative"
    assert ground("run at 11 km/h")["mode"] == "quantitative"


def test_routing_edge_cases():
    # casi limite del router qual/quant
    assert ground("let's do a 5k")["mode"] == "qualitative"          # niente unità note
    assert ground("push as hard as you can")["mode"] == "qualitative"  # solo parole
    assert ground("steady for 90 minutes")["mode"] == "quantitative"   # durata
    assert ground("90 minuti tranquilli")["mode"] == "quantitative"    # unità italiana


def test_surgical_bpm_from_speed():
    # 12 km/h -> cadence 134 + 2.9*12 = 168.8 -> BPM 168.8 (1:1), 84.4 (half)
    assert target_cadence_from_speed(12.0) == 168.8
    t = target_bpm(12.0)
    assert t["bpm_one_to_one"] == 168.8 and t["bpm_half_time"] == 84.4


def test_quantitative_prompt_grounds_precise_bpm():
    r = ground("tempo run at 12 km/h")
    assert r["bpm_target"]["bpm_one_to_one"] == 168.8
    assert r["shacl_ok"]


def test_qualitative_prompt_has_no_precise_bpm():
    r = ground("I feel tired, something easy")
    assert r["bpm_target"] is None       # defers to the HR bridge


def test_prf1_helper():
    m = prf1({"a", "b"}, {"a", "c"})
    assert m["precision"] == 0.5 and m["recall"] == 0.5 and m["f1"] == 0.5


def test_baseline_benchmark_is_strong():
    """The dictionary baseline should score high on the gold prompts."""
    m = evaluate(GOLD)
    assert m["f1"] >= 0.80, m
