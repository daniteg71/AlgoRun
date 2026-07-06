"""Distanza semantica fra generi sul grafo della tassonomia (ontology/genres.ttl).

BFS sull'albero skos:broader (leaf -> famiglia -> super-famiglia -> radice),
normalizzata in [0, 1]: stessa famiglia ~vicino, super-famiglie diverse ~1.
Nessun reasoner — e' l'unico uso a runtime dell'ontologia nel recommender.
"""
from __future__ import annotations

from collections import deque
from pathlib import Path

from rdflib import Graph
from rdflib.namespace import RDFS, SKOS

_GENRES_TTL = Path(__file__).parents[2] / "ontology" / "genres.ttl"

_ADJ: dict[str, set[str]] = {}          # adiacenza non orientata sul grafo skos
_LABEL: dict[str, str] = {}             # etichetta -> IRI del concetto
_CACHE: dict[tuple[str, str], float] = {}
_MAXPATH = 1                            # cammino piu' lungo (foglia -> radice -> foglia)


def _load() -> None:
    g = Graph().parse(_GENRES_TTL, format="turtle")
    for node, lab in g.subject_objects(RDFS.label):
        _LABEL[str(lab)] = str(node)
    for child, parent in g.subject_objects(SKOS.broader):
        _ADJ.setdefault(str(child), set()).add(str(parent))
        _ADJ.setdefault(str(parent), set()).add(str(child))
    global _MAXPATH
    root = _LABEL.get("music")
    _MAXPATH = 2 * max((_hops(leaf, root) or 0) for leaf in _LABEL.values())


def _hops(a: str, b: str) -> int | None:
    """Numero di archi sul cammino minimo a->b, o None se scollegati."""
    if a == b:
        return 0
    seen, queue = {a}, deque([(a, 0)])
    while queue:
        node, d = queue.popleft()
        for nxt in _ADJ.get(node, ()):
            if nxt == b:
                return d + 1
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, d + 1))
    return None


def genre_distance(genre_a: str, genre_b: str) -> float:
    """Distanza semantica [0, 1] fra due generi (0 = vicini, 1 = lontani/ignoti)."""
    if not _ADJ:
        _load()
    key = (genre_a, genre_b)
    if key not in _CACHE:
        a, b = _LABEL.get(genre_a), _LABEL.get(genre_b)
        hops = _hops(a, b) if a and b else None
        _CACHE[key] = 1.0 if hops is None else min(1.0, hops / _MAXPATH)
    return _CACHE[key]


if __name__ == "__main__":
    for a, b in [("techno", "detroit-techno"), ("techno", "house"),
                 ("techno", "classical"), ("punk", "hardcore"), ("jazz", "death-metal")]:
        print(f"{a:>10} <-> {b:<14} = {genre_distance(a, b):.3f}")
