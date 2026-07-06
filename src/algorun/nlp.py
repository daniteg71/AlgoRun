"""Estrazione entità per la Data Refinery (traccia d'esame Block 14):
dictionary matching longest-match-first sulle label OWL -> entità con IRI.

Il routing d'intento del PRODOTTO (tipo di corsa, numeri, parametri) NON sta piu'
qui: vive in `intent.py` (SetFit + regex). Questo modulo resta solo l'estrattore
che alimenta il refinery/KG.
"""
from __future__ import annotations

from rdflib.namespace import RDF

from algorun.ontology.loader import load_ontology


def dictionary_extract(text: str) -> list[dict]:
    """Baseline NER: longest-match-first sulle label OWL (ordinate dalla piu'
    lunga alla piu' corta), marcando i caratteri gia' presi per evitare overlap.
    Ritorna [{surface, iri, type_iri, start, end}].
    """
    schema = load_ontology()
    lowered = text.lower()
    taken = [False] * len(text)
    entities: list[dict] = []
    for surface, iri, kind in schema.label_dictionary():   # longest-first
        if kind != "individual":
            continue
        start = lowered.find(surface)
        while start != -1:
            end = start + len(surface)
            if not any(taken[start:end]):
                type_iri = next(schema.graph.objects(iri, RDF.type), None)
                entities.append({"surface": surface, "iri": str(iri),
                                 "type_iri": str(type_iri) if type_iri else None,
                                 "start": start, "end": end})
                for i in range(start, end):
                    taken[i] = True
            start = lowered.find(surface, end)
    entities.sort(key=lambda e: e["start"])
    return entities
