# test del modulo GPS: Haversine, smoothing, conversioni e target musicale.
# la fixture simula una corsa verso nord a velocità costante nota, così la
# velocità ricostruita con Haversine si può confrontare con la verità.

import numpy as np
import pandas as pd
import pytest

from algorun.sensors.gps import (clean_speed_kmh, gps_window_summary,
                                 haversine_m, pace_min_per_km, speed_series)

# 1 grado di latitudine ≈ 111 195 m -> a 12 km/h (3.333 m/s) il passo per
# secondo in gradi di latitudine è 3.333 / 111195
_DEG_PER_M_LAT = 1.0 / 111_195.0
SPEED_MS = 12.0 / 3.6          # 12 km/h in m/s


def _window(seconds: int = 30, with_speed_col: bool = False) -> pd.DataFrame:
    lat0, lon0 = 41.9028, 12.4964            # Roma
    rows = []
    for s in range(seconds):
        rows.append({
            "seconds_elapsed": float(s),
            "latitude": lat0 + SPEED_MS * s * _DEG_PER_M_LAT,
            "longitude": lon0,
            "horizontalAccuracy": 5.0,
        })
    df = pd.DataFrame(rows)
    if with_speed_col:
        df["speed"] = SPEED_MS
    return df


def test_haversine_one_lat_degree():
    # un grado di latitudine deve valere ~111.2 km
    d = haversine_m(41.0, 12.0, 42.0, 12.0)
    assert d == pytest.approx(111_195, rel=0.01)


def test_speed_from_haversine_matches_truth():
    v = speed_series(_window())
    # dal secondo campione in poi la velocità ricostruita è ~3.33 m/s
    assert float(v.iloc[5:].mean()) == pytest.approx(SPEED_MS, rel=0.02)


def test_speed_column_is_preferred():
    v = speed_series(_window(with_speed_col=True))
    assert float(v.iloc[0]) == pytest.approx(SPEED_MS)


def test_clean_speed_kmh_smoothing():
    kmh = clean_speed_kmh(_window(with_speed_col=True))
    assert float(kmh.iloc[-1]) == pytest.approx(12.0, rel=0.01)


def test_inaccurate_fixes_are_dropped():
    df = _window(with_speed_col=True)
    df.loc[10, "horizontalAccuracy"] = 50.0      # fix scadente -> scartato
    kmh = clean_speed_kmh(df)
    assert len(kmh) == len(df) - 1


def test_pace_and_summary():
    assert pace_min_per_km(12.0) == 5.0          # 12 km/h = 5:00 min/km
    s = gps_window_summary(_window(with_speed_col=True))
    assert s["current_kmh"] == pytest.approx(12.0, rel=0.01)
    # 12 km/h -> cadenza 168.8 -> BPM 168.8 (stessa regressione di nlp.py)
    assert s["music_target"]["bpm_one_to_one"] == pytest.approx(168.8, abs=0.3)
