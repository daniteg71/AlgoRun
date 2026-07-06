"""Integrazione: l'anello gira sui dati veri del sensore e sceglie canzoni."""
from pathlib import Path

import pytest

_SONGS = Path(__file__).parents[1] / "data" / "music" / "songs.csv"
pytestmark = pytest.mark.skipif(not _SONGS.exists(),
                                reason="data/music/songs.csv assente (git-ignored)")

INTENT = {"type": "tempo", "params": {"bpm": (155, 165), "energy": 0.8,
                                      "w_bpm": 0.7, "w_mood": 0.3, "tau": 0.1}}


def test_run_session_produces_trajectory():
    from algorun.controller import run_session
    from algorun.sensor import sessions
    traj = run_session(sessions()[0], INTENT)
    assert traj, "traiettoria vuota"
    step = traj[0]
    assert {"mean_hrr", "effort", "target_bpm", "song"} <= step.keys()
    assert 100 <= step["target_bpm"] <= 200


def test_safety_override_forces_low_target():
    from algorun.controller import adapt
    bpm, energy = adapt(INTENT["params"], "tempo", mean_hrr=0.95, effort="VeryHighEffort")
    assert bpm == 155 and energy <= 0.30      # cuore a mille -> banda bassa
