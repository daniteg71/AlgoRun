# il seguente codice trasforma l'export GPS di Sensor Logger (Location.csv)
# in una serie di velocità pulita, pronta per l'ontologia
#
# il codice nel complesso lavora in questo modo:
#
#   Location.csv (Sensor Logger)
#        ↓
#   filtro dei fix imprecisi (horizontalAccuracy)
#        ↓
#   velocità: colonna 'speed' del GPS, oppure formula di Haversine
#        ↓
#   smoothing con media mobile (il GPS è rumoroso)
#        ↓
#   conversioni: m/s → km/h → passo min/km
#        ↓
#   cadenza target e BPM target (stessa regressione di nlp.py)
#
#
# MATEMATICA UTILIZZATA:
#
# 1) Formula di Haversine — distanza fra due punti (lat/lon) sulla sfera:
#       a = sin²(Δφ/2) + cos(φ1)·cos(φ2)·sin²(Δλ/2)
#       d = 2·R·asin(√a)          con R = 6 371 000 m (raggio terrestre)
#    Serve come ripiego se la colonna 'speed' manca: v_i = d_i / Δt_i.
#
# 2) Media mobile (smoothing) — il GPS oscilla di ±1-2 m per fix, quindi la
#    velocità istantanea "balla"; una media mobile su W secondi la stabilizza
#    (stessa idea dell'isteresi usata per il battito).
#
# 3) Velocità → cadenza → BPM — riusa la regressione di nlp.py
#    (cadenza ≈ 134 + 2.9·km/h, limitata a [150, 190]) e l'entrainment
#    1:1 / half-time (Van Dyck et al. 2015).
#
# formato Location.csv di Sensor Logger (colonne che ci servono):
#   seconds_elapsed, latitude, longitude, speed (m/s), horizontalAccuracy (m)


from __future__ import annotations

import math

import numpy as np
import pandas as pd

from algorun.nlp import target_bpm

# raggio medio terrestre in metri (per Haversine)
EARTH_RADIUS_M = 6_371_000.0

# scartiamo i fix GPS con accuratezza orizzontale peggiore di questa soglia
MAX_HORIZONTAL_ACCURACY_M = 20.0

# finestra della media mobile sulla velocità (in campioni ≈ secondi a 1 Hz)
DEFAULT_SMOOTH_WINDOW = 5


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distanza in metri fra due coordinate (formula di Haversine)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def speed_series(df: pd.DataFrame) -> pd.Series:
    """Serie di velocità in m/s da un DataFrame in formato Location.csv.

    Preferisce la colonna 'speed' del GPS (già in m/s); se manca la
    ricostruisce con Haversine fra fix consecutivi: v_i = d_i / Δt_i.
    """
    if "speed" in df.columns and df["speed"].notna().any():
        return df["speed"].astype(float)

    # ripiego: distanza fra punti consecutivi / tempo trascorso
    lat = df["latitude"].astype(float).to_numpy()
    lon = df["longitude"].astype(float).to_numpy()
    t = df["seconds_elapsed"].astype(float).to_numpy()
    v = np.zeros(len(df))
    for i in range(1, len(df)):
        dt = t[i] - t[i - 1]
        if dt > 0:
            v[i] = haversine_m(lat[i - 1], lon[i - 1], lat[i], lon[i]) / dt
    return pd.Series(v, index=df.index)


def clean_speed_kmh(df: pd.DataFrame,
                    smooth_window: int = DEFAULT_SMOOTH_WINDOW) -> pd.Series:
    """Velocità pulita in km/h: filtro accuratezza + media mobile.

    - scarta i fix con horizontalAccuracy > 20 m (fix inaffidabili);
    - media mobile su `smooth_window` campioni (riduce il rumore GPS);
    - conversione m/s → km/h (× 3.6).
    """
    if "horizontalAccuracy" in df.columns:
        df = df[df["horizontalAccuracy"].astype(float) <= MAX_HORIZONTAL_ACCURACY_M]

    v_ms = speed_series(df)
    v_smooth = v_ms.rolling(window=smooth_window, min_periods=1).mean()
    return v_smooth * 3.6


def pace_min_per_km(speed_kmh: float) -> float:
    """Conversione velocità → passo (min/km): pace = 60 / km/h."""
    if speed_kmh <= 0:
        raise ValueError("speed must be positive")
    return round(60.0 / speed_kmh, 2)


def gps_window_summary(df: pd.DataFrame) -> dict:
    """Riassunto di una finestra GPS, simmetrico a PhysiologicalAnalysis.

    Ritorna velocità media/attuale (km/h), passo, e il target musicale
    chirurgico (cadenza + BPM 1:1 / half-time) dalla velocità attuale.
    Questo dict è quello che il ponte userà per il ramo quantitativo.
    """
    kmh = clean_speed_kmh(df)
    if kmh.empty:
        raise ValueError("no valid GPS fixes in the window")
    current = float(kmh.iloc[-1])
    mean = float(kmh.mean())
    return {
        "current_kmh": round(current, 2),
        "mean_kmh": round(mean, 2),
        "pace_min_km": pace_min_per_km(current) if current > 0 else None,
        "music_target": target_bpm(current) if current > 0 else None,
    }
