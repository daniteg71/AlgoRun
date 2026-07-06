"""Scelta della canzone: distanza pesata al target + selezione softmax.

- distanza BPM con correzione d'ottava (match a 1:1 / half / double, Van Dyck 2015);
- distanza di genere via genre_graph (shortest-path, Rada 1989);
- selezione softmax(-Score/tau) = exploration/exploitation (Sutton & Barto);
  tau alto -> esplora, tau -> 0 -> prende il match migliore.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from algorun.genre_graph import genre_distance

_SONGS = Path(__file__).parents[2] / "data" / "music" / "songs.csv"
_CATALOG = None


def catalog(path: Path = _SONGS) -> pd.DataFrame:
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = pd.read_csv(path)
    return _CATALOG


def _center(band: tuple[int, int]) -> float:
    return (band[0] + band[1]) / 2


def make_target(params: dict, bpm: float | None = None,
                energy: float | None = None, genre: str | None = None) -> dict:
    """Costruisce il target dallo strato NLP (+ eventuali valori dai sensori)."""
    w_bpm = params["w_bpm"]
    rest = (1.0 - w_bpm) / 2.0
    return {
        "bpm": bpm if bpm is not None else _center(params["bpm"]),
        "energy": energy if energy is not None else params["energy"],
        "genre": genre,
        "weights": {"bpm": w_bpm, "energy": rest, "genre": rest},
        "tau": params["tau"],
    }


def bpm_distance(song_bpm: float, bpm_target: float) -> float:
    """Distanza BPM relativa, corretta per l'ottava (1:1 / half / double)."""
    return min(abs(song_bpm * m - bpm_target) for m in (0.5, 1.0, 2.0)) / bpm_target


def score_row(row, target: dict) -> float:
    w = target["weights"]
    d_bpm = bpm_distance(row["bpm"], target["bpm"])
    d_energy = abs(row["energy"] - target["energy"])
    d_genre = genre_distance(target["genre"], row["genre"]) if target.get("genre") else 0.0
    return w["bpm"] * d_bpm + w["energy"] * d_energy + w["genre"] * d_genre


def choose(target: dict, exclude=(), df: pd.DataFrame | None = None, rng=None):
    """Ritorna la riga-canzone scelta: softmax se tau alto, altrimenti il minimo."""
    df = catalog() if df is None else df
    cand = df[~df["song_id"].isin(exclude)] if "song_id" in df.columns else df
    scores = cand.apply(lambda r: score_row(r, target), axis=1).to_numpy()
    tau = max(target.get("tau", 0.3), 1e-3)
    if tau <= 0.05:                              # exploitation puro
        return cand.iloc[int(scores.argmin())]
    logits = -scores / tau
    p = np.exp(logits - logits.max())
    p /= p.sum()
    idx = (rng or np.random).choice(len(cand), p=p)   # exploration
    return cand.iloc[int(idx)]
