"""End-to-end test of the bridge: simulated BPM -> ontology -> SHACL -> target."""

from algorun.pipeline import SAFE_MAX_FRACTION, decide, _demo_window

REST, MAX = 60.0, 195.0


def _decide(bpm_level: float, goal: str = "interval"):
    analysis = _demo_window(bpm_level, REST, MAX)
    return decide(analysis, REST, MAX, goal)


def test_low_effort_gets_calm_target_and_passes_shacl():
    d = _decide(100)                       # ~HRR 0.34
    assert d["effort"] == "LowEffort"
    assert d["shacl_ok"]
    assert d["target"]["bpm_max"] == 110   # RecoveryTarget 90-110


def test_high_effort_gets_energetic_target():
    d = _decide(165)                       # ~HRR 0.82
    assert d["effort"] == "HighEffort"
    assert d["shacl_ok"]
    assert d["target"]["bpm_min"] == 130   # ThresholdTarget 130-150


def test_danger_zone_forces_recovery():
    """Above 93% HRmax the safety override forces a calm target."""
    d = _decide(185)                       # current ~191 >= safe max 181
    assert d["effort"] == "VeryHighEffort"
    assert d["hr"] >= MAX * SAFE_MAX_FRACTION
    assert d["forced_recovery"]
    assert d["target"]["bpm_max"] == 110   # forced RecoveryTarget


def test_generated_graph_is_valid_and_consistent():
    """The simulated data really activates the ontology (SHACL + reasoner)."""
    from algorun.ontology.evaluation import check_consistency
    from algorun.pipeline import window_to_graph
    analysis = _demo_window(135, REST, MAX)
    graph = window_to_graph(analysis, REST, MAX, "interval")
    assert check_consistency(graph)        # HermiT: still logically consistent
