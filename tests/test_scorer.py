"""Test dello scoring: distanza BPM con ottava e costruzione del target."""
from algorun.scorer import bpm_distance, make_target

_P = {"bpm": (150, 170), "energy": 0.8, "w_bpm": 0.7, "w_mood": 0.3, "tau": 0.2}


def test_bpm_distance_exact_is_zero():
    assert bpm_distance(180, 180) == 0.0


def test_bpm_distance_half_time_matches():
    # 90 bpm a doppio tempo = 180 -> distanza 0
    assert bpm_distance(90, 180) == 0.0


def test_bpm_distance_relative():
    # 175 vs 180 -> 5/180
    assert bpm_distance(175, 180) == 5 / 180


def test_make_target_weights_sum_to_one():
    t = make_target(_P)
    w = t["weights"]
    assert abs(w["bpm"] + w["energy"] + w["genre"] - 1.0) < 1e-9
    assert t["bpm"] == 160 and t["energy"] == 0.8       # centro banda, energia


def test_make_target_overrides_from_sensor():
    t = make_target(_P, bpm=165, energy=0.6)
    assert t["bpm"] == 165 and t["energy"] == 0.6
