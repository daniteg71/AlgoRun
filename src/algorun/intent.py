"""NLP del prodotto: frase -> {type, numbers, params}.

Regex per i numeri (SetFit non estrae valori) + SetFit per il tipo di corsa.
I `params` per tipo NON sono random: banda BPM ancorata alla cadenza naturale di
corsa 150-190 spm e all'entrainment cadenza=BPM (Van Dyck 2015); l'energia alla
teoria arousal-musica (Karageorghis & Terry 2009). Bande/pesi/tau esatti = scelte
di design, da giustificare con ablation nel paper.
"""
from __future__ import annotations

import re
from pathlib import Path

_MODEL = None
_MODEL_DIR = Path(__file__).parents[2] / "models" / "intent-setfit"

# numeri: velocità km/h, passo min/km, distanza km, durata min
_SPEED = re.compile(r"(\d+(?:[.,]\d+)?)\s*km\s*/?\s*h", re.I)
_PACE = re.compile(r"(\d{1,2}):(\d{2})\s*(?:min)?\s*/?\s*km", re.I)
_DIST = re.compile(r"(\d+(?:[.,]\d+)?)\s*km(?!\s*/?\s*h)", re.I)
_DUR = re.compile(r"(\d+)\s*(?:min|minuti)\b", re.I)

# tipo -> (banda BPM, energia target, pesi scoring, temperatura esplorazione)
TYPE_PARAMS: dict[str, dict] = {
    "easy":     {"bpm": (120, 135), "energy": 0.25, "w_bpm": 0.2, "w_mood": 0.8, "tau": 1.0},
    "long":     {"bpm": (135, 150), "energy": 0.50, "w_bpm": 0.5, "w_mood": 0.5, "tau": 0.4},
    "tempo":    {"bpm": (155, 165), "energy": 0.80, "w_bpm": 0.7, "w_mood": 0.3, "tau": 0.2},
    "interval": {"bpm": (170, 185), "energy": 0.95, "w_bpm": 0.9, "w_mood": 0.1, "tau": 0.1},
    "fartlek":  {"bpm": (120, 170), "energy": 0.60, "w_bpm": 0.4, "w_mood": 0.6, "tau": 1.0},
}


# mood -> genere-seme sull'albero dei generi (mood-oriented).
# arousal/valenza -> genere (Russell 1980); i generi esistono in genres.ttl.
MOOD_SEED: dict[str, str] = {
    "carico": "metal", "carica": "metal", "gasato": "edm", "energico": "edm",
    "arrabbiato": "hardcore", "incazzato": "hardcore", "grintoso": "hard-rock",
    "concentrato": "minimal-techno", "felice": "happy", "allegro": "happy",
    "chill": "chill", "tranquillo": "ambient", "rilassato": "ambient",
    "calmo": "ambient", "triste": "sad", "malinconico": "sad", "funky": "funk",
}


def detect_mood_seed(text: str) -> tuple[str | None, str | None]:
    """Cerca una parola di mood nella frase -> (mood, genere-seme) o (None, None)."""
    low = text.lower()
    for word, genre in MOOD_SEED.items():
        if word in low:
            return word, genre
    return None, None


def _model():
    global _MODEL
    if _MODEL is None:
        from setfit import SetFitModel
        _MODEL = SetFitModel.from_pretrained(str(_MODEL_DIR))
    return _MODEL


def parse_numbers(text: str) -> dict:
    n: dict = {}
    if (m := _SPEED.search(text)):
        n["speed_kmh"] = float(m.group(1).replace(",", "."))
    elif (m := _PACE.search(text)):
        pace = int(m.group(1)) + int(m.group(2)) / 60
        n["speed_kmh"] = round(60 / pace, 1) if pace else None
    if (m := _DIST.search(text)):
        n["distance_km"] = float(m.group(1).replace(",", "."))
    if (m := _DUR.search(text)):
        n["duration_min"] = int(m.group(1))
    return n


def route(text: str) -> dict:
    """Frase -> {type, mood, genre_seed, numbers, params}. Input dello scorer."""
    wtype = _model().predict([text])[0]
    mood, genre_seed = detect_mood_seed(text)
    return {"type": wtype, "mood": mood, "genre_seed": genre_seed,
            "numbers": parse_numbers(text), "params": TYPE_PARAMS[wtype]}


if __name__ == "__main__":
    import sys
    print(route(" ".join(sys.argv[1:]) or "oggi ripetute veloci a 12 km/h"))
