"""Test dell'intento prodotto — solo la parte regex + tabella (niente modello).

`route()` carica SetFit (torch): fuori dalla suite veloce. Qui si testa
`parse_numbers` (deterministico) e la coerenza di TYPE_PARAMS.
"""
from algorun.intent import (TYPE_PARAMS, bpm_from_speed, detect_mood_seed,
                            parse_numbers)


def test_bpm_from_speed():
    assert bpm_from_speed(12) == 169     # 134 + 2.9*12 = 168.8 -> 169
    assert bpm_from_speed(3) == 150      # clamp minimo (cadenza naturale)
    assert bpm_from_speed(40) == 190     # clamp massimo


def test_mood_maps_to_seed_genre():
    assert detect_mood_seed("oggi sono carico")[1] == "metal"
    assert detect_mood_seed("qualcosa di chill")[1] == "chill"
    assert detect_mood_seed("corsa normale") == (None, None)


def test_parse_speed_kmh():
    assert parse_numbers("corro a 12 km/h")["speed_kmh"] == 12.0


def test_parse_pace_minkm_to_speed():
    # 5:00 min/km -> 12 km/h
    assert parse_numbers("tengo 5:00 min/km")["speed_kmh"] == 12.0


def test_distance_not_confused_with_speed():
    n = parse_numbers("oggi 10 km")
    assert n.get("distance_km") == 10.0 and "speed_kmh" not in n


def test_parse_duration():
    assert parse_numbers("30 minuti tranquilli")["duration_min"] == 30


def test_five_types_and_weights_sum_to_one():
    assert set(TYPE_PARAMS) == {"easy", "long", "tempo", "interval", "fartlek"}
    for p in TYPE_PARAMS.values():
        assert 0.0 <= p["energy"] <= 1.0
        assert abs(p["w_bpm"] + p["w_mood"] - 1.0) < 1e-9
