"""Test dell'analisi fisiologica (HRR, sforzo, trend)."""
import pytest

from algorun.sensor import (analyze_bpm_window, classify_effort, classify_trend,
                            compute_hrr)


def test_hrr_karvonen():
    # (130-60)/(200-60) = 0.5
    assert compute_hrr(130, 60, 200) == pytest.approx(0.5)


def test_hrr_invalid_profile_raises():
    with pytest.raises(ValueError):
        compute_hrr(130, 200, 60)     # max <= rest


def test_effort_zones():
    assert classify_effort(0.30) == "LowEffort"
    assert classify_effort(0.50) == "TargetEffort"
    assert classify_effort(0.80) == "HighEffort"
    assert classify_effort(0.95) == "VeryHighEffort"


def test_trend_zones():
    assert classify_trend(0.2) == "Increasing"
    assert classify_trend(-0.2) == "Decreasing"
    assert classify_trend(0.0) == "Stable"


def test_analyze_window_detects_rising_effort():
    shot = analyze_bpm_window([140, 145, 150, 155, 160], resting_hr=60, max_hr=200)
    assert shot.trend_state == "Increasing"
    assert 0.0 <= shot.current_hrr <= 1.2
