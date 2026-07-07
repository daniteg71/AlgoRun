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


def adapt(params: dict, wtype: str, mean_hrr: float, effort: str,
          base_bpm: float | None = None) -> tuple[float, float]:
    """Aggiorna (bpm*, energy*) dagli shot. `base_bpm` = BPM dalla velocità
    dichiarata (regime quantitativo): se c'e' comanda lui, altrimenti la banda
    del tipo. Il cuore ha l'ultima parola (safety override)."""
    lo, hi = params["bpm"]
    bpm = base_bpm if base_bpm is not None else (lo + hi) / 2
    energy = params["energy"]
    if mean_hrr >= SAFE_HRR:                                  # safety: HR pericolosa -> recupero
        return lo, min(energy, 0.30)                          # (ignora l'intento "spingere")
    if wtype == "tempo" and effort == "LowEffort":
        energy = min(1.0, energy * 1.2)                      # dici tempo ma vai piano -> spingi
    elif wtype == "easy" and effort in ("HighEffort", "VeryHighEffort"):
        energy = energy * 0.7                                # dici easy ma sali -> calma
    elif wtype == "fartlek":
        energy = (min(1.0, energy * 1.2)
                  if effort in ("HighEffort", "VeryHighEffort") else energy * 0.7)
    return bpm, energy


def run_session(session_id: str, intent: dict, shots_per_song: int = 6,
                memory: int = 3) -> list[dict]:
    """Riproduce la sessione sui dati del sensore e restituisce la traiettoria
    (una voce per canzone): sforzo osservato -> target aggiornato -> canzone scelta.
    """
    params, wtype = intent["params"], intent["type"]
    base_bpm = intent.get("target_bpm")            # BPM dalla velocità dichiarata, se c'e'
    shots = read_session_shots(session_id)
    played: deque = deque(maxlen=memory)
    trajectory: list[dict] = []
    for i in range(0, len(shots), shots_per_song):
        chunk = shots[i:i + shots_per_song]
        if not chunk:
            break
        m_hrr = mean(s["mean_hrr"] for s in chunk)
        effort = Counter(s["effort_state"] for s in chunk).most_common(1)[0][0]
        bpm, energy = adapt(params, wtype, m_hrr, effort, base_bpm=base_bpm)
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
