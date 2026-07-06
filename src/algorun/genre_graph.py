"""Distanza semantica fra generi sul grafo della tassonomia (ontology/genres.ttl).

Compila l'albero skos:broader (leaf -> famiglia -> super-famiglia -> radice) in
una lista di adiacenza e misura la vicinanza fra due generi come lunghezza del
cammino minimo, normalizzata in [0, 1]. Due generi nella stessa famiglia sono
vicini (~0); generi in super-famiglie diverse sono lontani (~1).

Questo e' l'unico uso a runtime dell'ontologia nel recommender: nessun reasoner,
solo una BFS su un grafo di poche centinaia di nodi caricato una volta.
"""
from __future__ import annotations

from collections import deque
from functools import lru_cache
from pathlib import Path

from rdflib import Graph
from rdflib.namespace import SKOS, RDFS

GENRES_TTL = Path(__file__).parents[2] / "ontology" / "genres.ttl"


class GenreTaxonomy:
    def __init__(self, ttl_path: Path = GENRES_TTL):
        g = Graph().parse(ttl_path, format="turtle")
        # etichetta -> IRI del concetto foglia/famiglia
        self.by_label: dict[str, str] = {
            str(lab): str(node) for node, lab in g.subject_objects(RDFS.label)
        }
        # adiacenza non orientata sugli archi skos:broader
        self.adj: dict[str, set[str]] = {}
        for child, parent in g.subject_objects(SKOS.broader):
            c, p = str(child), str(parent)
            self.adj.setdefault(c, set()).add(p)
            self.adj.setdefault(p, set()).add(c)
        self._diameter = self._compute_diameter()

    def _hops(self, a: str, b: str) -> int | None:
        if a == b:
            return 0
        seen = {a}
        q: deque[tuple[str, int]] = deque([(a, 0)])
        while q:
            node, d = q.popleft()
            for nxt in self.adj.get(node, ()):
                if nxt == b:
                    return d + 1
                if nxt not in seen:
                    seen.add(nxt)
                    q.append((nxt, d + 1))
        return None

    def _compute_diameter(self) -> int:
        # nell'albero il cammino massimo e' foglia -> radice -> foglia = 2 * profondita'
        root = self.by_label.get("music")
        depth = max((self._hops(leaf, root) or 0) for leaf in self.by_label.values())
        return 2 * depth

    @lru_cache(maxsize=4096)
    def distance(self, genre_a: str, genre_b: str) -> float:
        """Distanza normalizzata in [0, 1]. 1.0 se un genere e' sconosciuto."""
        a = self.by_label.get(genre_a)
        b = self.by_label.get(genre_b)
        if a is None or b is None:
            return 1.0
        hops = self._hops(a, b)
        if hops is None:
            return 1.0
        return min(1.0, hops / self._diameter)


_TAXONOMY: GenreTaxonomy | None = None


def genre_distance(genre_a: str, genre_b: str) -> float:
    """Distanza semantica [0,1] fra due generi (0 = identici/vicini, 1 = lontani)."""
    global _TAXONOMY
    if _TAXONOMY is None:
        _TAXONOMY = GenreTaxonomy()
    return _TAXONOMY.distance(genre_a, genre_b)


if __name__ == "__main__":
    for a, b in [("techno", "detroit-techno"), ("techno", "house"),
                 ("techno", "classical"), ("punk", "hardcore"), ("jazz", "death-metal")]:
        print(f"{a:>10} <-> {b:<14} = {genre_distance(a, b):.3f}")
