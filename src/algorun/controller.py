"""Anello di controllo. Durante ogni canzone si osservano gli shot del sensore;
a fine canzone si aggiorna il target (in base al tipo di corsa e allo sforzo
misurato) e si sceglie la prossima canzone. Il cuore comanda: safety override.

Comportamento per tipo:
  easy    -> se lo sforzo sale troppo, tira giu' (banda bassa, energia giu')
  tempo   -> se sei sotto la zona target, spingi su (energia su)
  fartlek -> segui il runner (sale->su, scende->giu')
  long/interval/base -> tieni la banda (interval = onda quadra a timer, TODO)
"""
from __future__ import annotations

from collections import Counter, deque
from statistics import mean

from algorun import scorer
from algorun.sensor import read_session_shots

SAFE_HRR = 0.90          # oltre questa HRR: forza recupero (design, ~limite fisiologico)


def adapt(params: dict, wtype: str, mean_hrr: float, effort: str) -> tuple[float, float]:
    """Aggiorna (bpm*, energy*) dagli shot, secondo il tipo. Ritorna (bpm, energy)."""
    lo, hi = params["bpm"]
    bpm, energy = (lo + hi) / 2, params["energy"]
    if mean_hrr >= SAFE_HRR:                                  # safety: rallenta sempre
        return lo, min(energy, 0.30)
    if wtype == "easy" and effort in ("HighEffort", "VeryHighEffort"):
        return lo, energy * 0.7                              # sta salendo -> tira giu'
    if wtype == "tempo" and effort == "LowEffort":
        return hi, min(1.0, energy * 1.2)                    # sotto target -> spingi su
    if wtype == "fartlek":
        up = effort in ("HighEffort", "VeryHighEffort")
        return (hi, min(1.0, energy * 1.2)) if up else (lo, energy * 0.7)
    return bpm, energy                                       # long/interval/base: tieni


def run_session(session_id: str, intent: dict, shots_per_song: int = 6,
                memory: int = 3) -> list[dict]:
    """Riproduce la sessione sui dati del sensore e restituisce la traiettoria
    (una voce per canzone): sforzo osservato -> target aggiornato -> canzone scelta.
    """
    params, wtype = intent["params"], intent["type"]
    shots = read_session_shots(session_id)
    played: deque = deque(maxlen=memory)
    trajectory: list[dict] = []
    for i in range(0, len(shots), shots_per_song):
        chunk = shots[i:i + shots_per_song]
        if not chunk:
            break
        m_hrr = mean(s["mean_hrr"] for s in chunk)
        effort = Counter(s["effort_state"] for s in chunk).most_common(1)[0][0]
        bpm, energy = adapt(params, wtype, m_hrr, effort)
        target = scorer.make_target(params, bpm=bpm, energy=energy,
                                    genre=intent.get("genre_seed"))
        song = scorer.choose(target, exclude=set(played))
        played.append(song["song_id"])
        trajectory.append({"mean_hrr": round(m_hrr, 2), "effort": effort,
                           "target_bpm": round(bpm), "song": song["title"],
                           "song_bpm": round(float(song["bpm"]))})
    return trajectory


def _demo() -> None:
    from algorun.sensor import sessions
    sid = sessions()[0]
    intent = {"type": "easy", "params": {"bpm": (120, 135), "energy": 0.25,
                                         "w_bpm": 0.2, "w_mood": 0.8, "tau": 1.0}}
    print(f"Sessione {sid} come '{intent['type']}':")
    for step in run_session(sid, intent):
        print(f"  HRR {step['mean_hrr']:>4} {step['effort']:<14} "
              f"target {step['target_bpm']}bpm -> {step['song']} ({step['song_bpm']}bpm)")


if __name__ == "__main__":
    _demo()
