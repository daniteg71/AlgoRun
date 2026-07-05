# test della fusione prompt+sensore: le 3 regole di precedenza
# (sicurezza > prompt quantitativo validato > sensore) e la difesa in
# profondità del gate SHACL sul grafo combinato.

from algorun.fusion import _combined_graph, fuse
from algorun.nlp import ground
from algorun.pipeline import _demo_window, decide, validate

REST, MAX = 60.0, 195.0        # safe max = 181.35


def _fuse(text: str, hr_level: float) -> dict:
    prompt = ground(text)
    sensor = decide(_demo_window(hr_level, REST, MAX), REST, MAX, "interval")
    return fuse(prompt, sensor, REST, MAX)


def test_qualitative_prompt_sensor_wins():
    f = _fuse("I feel tired, something easy", 140)
    assert f["source"] == "sensor"
    assert f["target"]["bpm_min"] == 120       # TargetEffort -> EasyTarget


def test_quantitative_prompt_wins_when_safe():
    f = _fuse("tempo run at 12 km/h", 140)
    assert f["source"] == "prompt"
    assert f["target"]["bpm_one_to_one"] == 168.8
    assert f["shacl_ok"]


def test_safety_beats_quantitative_prompt():
    # il caso che prima era un buco: prompt dichiarato MA battito critico
    f = _fuse("tempo run at 12 km/h", 185)     # HR ~191 >= 181
    assert f["source"] == "safety"
    assert f["target"]["bpm_max"] == 110       # forzato RecoveryTarget


def test_shacl_gate_blocks_combined_graph():
    # difesa in profondità: anche senza la regola 1, il gate SHACL respinge
    # un target energico (168.8) con HR critico nello stesso grafo
    g = _combined_graph(prompt_bpm=168.8, current_hr=190,
                        resting_hr=REST, max_hr=MAX)
    ok, report = validate(g)
    assert not ok
    assert "heart rate" in report.lower()
