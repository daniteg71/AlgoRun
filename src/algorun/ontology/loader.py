"""Ontology loading and label-dictionary construction.

The ontology is the single source of truth for the whole pipeline
(GUIDELINES.md, Rule 1): every class, relation and surface form used by the
NLP stages is derived from `ontology/algorun.owl` at runtime, never hardcoded.

The label dictionary produced here feeds the baseline rule-based entity
detector (longest-string-match-first, per the course's "Classical Rule-Based"
approach) and the prompt construction for GLiNER / the synthetic data
generator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

AR = Namespace("http://algorun.org/ontology#")

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ONTOLOGY_PATH = _REPO_ROOT / "ontology" / "algorun.owl"
DEFAULT_SHAPES_PATH = _REPO_ROOT / "ontology" / "shapes.ttl"


@dataclass
class PropertySpec:
    """An object/data property with its explicit domain and range."""

    iri: URIRef
    label: str
    domain: URIRef | None
    range: URIRef | None
    surface_forms: list[str] = field(default_factory=list)


@dataclass
class OntologySchema:
    """Parsed view of the ontology used by every downstream stage."""

    graph: Graph
    classes: dict[URIRef, list[str]]            # class IRI -> surface forms
    individuals: dict[URIRef, list[str]]        # individual IRI -> surface forms
    object_properties: dict[URIRef, PropertySpec]
    data_properties: dict[URIRef, PropertySpec]

    def label_dictionary(self) -> list[tuple[str, URIRef, str]]:
        """Flat (surface_form, iri, kind) list, longest surface form first.

        Longest-match-first ordering implements the course-mandated mechanic
        of the classical rule-based entity detector.
        """
        entries: list[tuple[str, URIRef, str]] = []
        for iri, forms in self.classes.items():
            entries.extend((form, iri, "class") for form in forms)
        for iri, forms in self.individuals.items():
            entries.extend((form, iri, "individual") for form in forms)
        entries.sort(key=lambda e: len(e[0]), reverse=True)
        return entries

    def relation_dictionary(self) -> list[tuple[str, URIRef]]:
        """(trigger surface form, property IRI), longest first — used by the
        baseline trigger-word relation extractor."""
        entries: list[tuple[str, URIRef]] = []
        for spec in self.object_properties.values():
            entries.extend((form, spec.iri) for form in spec.surface_forms)
        entries.sort(key=lambda e: len(e[0]), reverse=True)
        return entries


def _surface_forms(graph: Graph, subject: URIRef) -> list[str]:
    """rdfs:label + all skos:altLabel, lowercased, deduplicated."""
    forms: list[str] = []
    for predicate in (RDFS.label, SKOS.altLabel):
        for value in graph.objects(subject, predicate):
            text = str(value).strip().lower()
            if text and text not in forms:
                forms.append(text)
    return forms


def _property_spec(graph: Graph, prop: URIRef) -> PropertySpec:
    label_values = list(graph.objects(prop, RDFS.label))
    return PropertySpec(
        iri=prop,
        label=str(label_values[0]) if label_values else str(prop),
        domain=next(graph.objects(prop, RDFS.domain), None),
        range=next(graph.objects(prop, RDFS.range), None),
        surface_forms=_surface_forms(graph, prop),
    )


def load_ontology(path: Path | str = DEFAULT_ONTOLOGY_PATH) -> OntologySchema:
    """Parse the OWL file (Turtle syntax) into an :class:`OntologySchema`."""
    graph = Graph()
    graph.parse(str(path), format="turtle")

    classes: dict[URIRef, list[str]] = {}
    for cls in graph.subjects(RDF.type, OWL.Class):
        if isinstance(cls, URIRef):
            classes[cls] = _surface_forms(graph, cls)

    individuals: dict[URIRef, list[str]] = {}
    for cls in classes:
        for ind in graph.subjects(RDF.type, cls):
            if isinstance(ind, URIRef) and ind not in classes:
                individuals[ind] = _surface_forms(graph, ind)

    object_properties = {
        prop: _property_spec(graph, prop)
        for prop in graph.subjects(RDF.type, OWL.ObjectProperty)
        if isinstance(prop, URIRef)
    }
    data_properties = {
        prop: _property_spec(graph, prop)
        for prop in graph.subjects(RDF.type, OWL.DatatypeProperty)
        if isinstance(prop, URIRef)
    }

    return OntologySchema(
        graph=graph,
        classes=classes,
        individuals=individuals,
        object_properties=object_properties,
        data_properties=data_properties,
    )


def load_shapes(path: Path | str = DEFAULT_SHAPES_PATH) -> Graph:
    """Parse the SHACL shapes file used by the semantic-grounding gate."""
    graph = Graph()
    graph.parse(str(path), format="turtle")
    return graph
