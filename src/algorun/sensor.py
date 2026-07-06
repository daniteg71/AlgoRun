"""Analisi fisiologica: finestra di BPM cardiaci -> HRR, sforzo, trend.

Logica del socio (physiological_state.py) compattata, stessa matematica:
HRR = Karvonen 1957; soglie di sforzo su HRR; trend = pendenza della regressione
lineare. Include il reader delle finestre gia' calcolate in
data/processed/physiological_windows.csv (che il controller consuma come "shot").
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

# soglie di sforzo su HRR: <0.40 Low, <0.70 Target, <0.85 High, else VeryHigh
LOW, TARGET, HIGH = 0.40, 0.70, 0.85
TREND_THRESHOLD = 0.05                       # bpm/s (~3 bpm) per Increasing/Decreasing
_WINDOWS = Path(__file__).parents[2] / "data" / "processed" / "physiological_windows.csv"


@dataclass(frozen=True)
class Shot:
    mean_bpm: float
    current_hrr: float
    mean_hrr: float
    effort_state: str
    trend_state: str

    def to_dict(self) -> dict:
        return asdict(self)


def compute_hrr(hr: float, resting_hr: float, max_hr: float) -> float:
    """HRR di Karvonen, limitata a [0, 1.2] per tollerare piccoli errori."""
    if resting_hr <= 0 or max_hr <= resting_hr:
        raise ValueError("profilo HR non valido: serve max_hr > resting_hr > 0")
    return float(np.clip((hr - resting_hr) / (max_hr - resting_hr), 0.0, 1.2))


def classify_effort(hrr: float) -> str:
    return ("LowEffort" if hrr < LOW else "TargetEffort" if hrr < TARGET
            else "HighEffort" if hrr < HIGH else "VeryHighEffort")


def classify_trend(slope_bpm_per_s: float, threshold: float = TREND_THRESHOLD) -> str:
    if threshold <= 0:
        raise ValueError("soglia di trend deve essere positiva")
    return ("Increasing" if slope_bpm_per_s > threshold
            else "Decreasing" if slope_bpm_per_s < -threshold else "Stable")


def analyze_bpm_window(bpm_values: Sequence[float], resting_hr: float,
                       max_hr: float, sampling_rate_hz: float = 1.0) -> Shot:
    """Sequenza di BPM cardiaci -> Shot (per un sensore reale/live)."""
    v = np.asarray(bpm_values, dtype=float)
    if v.ndim != 1 or len(v) < 2 or not np.isfinite(v).all() or np.any(v <= 0):
        raise ValueError("finestra BPM non valida (>=2 valori positivi e finiti)")
    seconds = np.arange(len(v), dtype=float) / sampling_rate_hz
    slope = float(np.polyfit(seconds, v, deg=1)[0])
    hrr = compute_hrr(float(v[-1]), resting_hr, max_hr)
    return Shot(float(v.mean()), hrr, compute_hrr(float(v.mean()), resting_hr, max_hr),
                classify_effort(hrr), classify_trend(slope))


def read_session_shots(session_id: str, path: Path = _WINDOWS) -> list[dict]:
    """Finestre gia' calcolate (HRR/effort/trend) di una sessione, in ordine."""
    df = pd.read_csv(path)
    df = df[df["session_id"] == session_id].sort_values("window_start_second")
    cols = ["window_start_second", "mean_hrr", "current_hrr", "effort_state",
            "trend_state", "mean_bpm"]
    return df[cols].to_dict("records")


def sessions(path: Path = _WINDOWS) -> list[str]:
    return sorted(pd.read_csv(path)["session_id"].unique())
