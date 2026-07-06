"""Test della distanza semantica fra generi sulla tassonomia."""
from algorun.genre_graph import genre_distance


def test_identita_e_zero():
    assert genre_distance("techno", "techno") == 0.0


def test_gradiente_semantico():
    # stessa famiglia < stessa super-famiglia < super-famiglie diverse
    same_family = genre_distance("techno", "detroit-techno")
    same_super = genre_distance("techno", "house")
    cross_super = genre_distance("techno", "classical")
    assert 0.0 < same_family < same_super < cross_super <= 1.0


def test_simmetria():
    assert genre_distance("jazz", "punk") == genre_distance("punk", "jazz")


def test_genere_sconosciuto_e_massimo():
    assert genre_distance("techno", "non-esiste") == 1.0


def test_range_valido():
    for a, b in [("pop", "rock"), ("salsa", "samba"), ("metal", "chill")]:
        assert 0.0 <= genre_distance(a, b) <= 1.0
