# =============================================================================
# COSA FA QUESTO FILE
# -----------------------------------------------------------------------------
# Carica l'ontologia (il file .owl) e la trasforma in oggetti Python comodi da
# usare nel resto del progetto. È il PONTE fra il file di conoscenza scritto in
# Turtle (ontology/algorun.owl) e il codice.
#
# In pratica produce due "dizionari" fondamentali che tutti gli altri moduli
# riusano invece di scrivere stringhe a mano (regola del corso: la conoscenza
# sta nell'ontologia, il codice la LEGGE, non la ripete):
#
#   1. label_dictionary()    -> tutte le forme testuali (label + sinonimi) con
#                               cui una classe o un individuo può comparire in
#                               una frase. Serve al NER a dizionario (nlp.py).
#   2. relation_dictionary() -> le parole-trigger di ogni relazione (es.
#                               "performs", "targets"). Serve all'estrazione
#                               delle relazioni (refinery.py).
#
# Entrambi ordinati dalla forma PIÙ LUNGA alla più corta ("longest-match-first",
# la meccanica richiesta dal corso: prima si prova a matchare "recovery run"
# poi "run", così non si spezza la frase male).
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

# prefisso della nostra ontologia: AR.Runner == http://algorun.org/ontology#Runner
AR = Namespace("http://algorun.org/ontology#")

# percorsi dei file: si risale di 3 cartelle (loader.py -> ontology -> algorun
# -> src) e poi si punta alla cartella ontology/ nella radice del repo
_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ONTOLOGY_PATH = _REPO_ROOT / "ontology" / "algorun.owl"
DEFAULT_SHAPES_PATH = _REPO_ROOT / "ontology" / "shapes.ttl"


@dataclass
class PropertySpec:
    """Descrive UNA relazione (object/data property) con il suo dominio e range.

    domain = da che tipo di soggetto può partire la relazione,
    range  = a che tipo di oggetto può arrivare.
    Es. performsSession: domain=Runner, range=WorkoutSession.
    surface_forms = le parole con cui la relazione compare nel testo (trigger).
    """

    iri: URIRef
    label: str
    domain: URIRef | None
    range: URIRef | None
    surface_forms: list[str] = field(default_factory=list)


@dataclass
class OntologySchema:
    """Vista completa dell'ontologia già "digerita", pronta all'uso.

    Contiene il grafo RDF grezzo più quattro indici comodi (classi, individui,
    object property, data property). I metodi qui sotto costruiscono i due
    dizionari usati dalla pipeline NLP.
    """

    graph: Graph
    classes: dict[URIRef, list[str]]            # IRI classe    -> forme testuali
    individuals: dict[URIRef, list[str]]        # IRI individuo -> forme testuali
    object_properties: dict[URIRef, PropertySpec]
    data_properties: dict[URIRef, PropertySpec]

    def label_dictionary(self) -> list[tuple[str, URIRef, str]]:
        """Lista piatta (forma_testuale, IRI, tipo) ordinata dalla più lunga.

        `tipo` è "class" o "individual". È il vocabolario che il NER a
        dizionario scorre per riconoscere le entità nel testo. L'ordinamento
        per lunghezza decrescente realizza il "longest-match-first" del corso.
        """
        entries: list[tuple[str, URIRef, str]] = []
        # prima le classi...
        for iri, forms in self.classes.items():
            entries.extend((form, iri, "class") for form in forms)
        # ...poi gli individui (Interval, WarmUp, LowEffort, ...)
        for iri, forms in self.individuals.items():
            entries.extend((form, iri, "individual") for form in forms)
        # ordina: la forma più lunga per prima (key = lunghezza, reverse=True)
        entries.sort(key=lambda e: len(e[0]), reverse=True)
        return entries

    def relation_dictionary(self) -> list[tuple[str, URIRef]]:
        """Lista (parola-trigger, IRI della relazione), più lunga per prima.

        Usata dall'estrattore di relazioni baseline: quando nel testo compare
        un trigger (es. "targets") sa a quale relazione corrisponde
        (ar:targetsEffort).
        """
        entries: list[tuple[str, URIRef]] = []
        for spec in self.object_properties.values():
            entries.extend((form, spec.iri) for form in spec.surface_forms)
        entries.sort(key=lambda e: len(e[0]), reverse=True)
        return entries


def _surface_forms(graph: Graph, subject: URIRef) -> list[str]:
    """Raccoglie tutte le forme testuali di un termine: rdfs:label + ogni
    skos:altLabel, in minuscolo e senza duplicati.

    È qui che i SINONIMI dell'ontologia (es. "pulse", "heartbeat" per
    HeartRateReading) diventano utilizzabili dal NER — è ciò che rende
    risolvibile il livello "implicit" del dataset.
    """
    forms: list[str] = []
    for predicate in (RDFS.label, SKOS.altLabel):
        for value in graph.objects(subject, predicate):
            text = str(value).strip().lower()
            if text and text not in forms:      # niente doppioni
                forms.append(text)
    return forms


def _property_spec(graph: Graph, prop: URIRef) -> PropertySpec:
    """Costruisce la PropertySpec di una relazione leggendo domain, range e
    forme testuali direttamente dal grafo RDF."""
    label_values = list(graph.objects(prop, RDFS.label))
    return PropertySpec(
        iri=prop,
        label=str(label_values[0]) if label_values else str(prop),
        # next(..., None): prende il primo domain/range dichiarato, o None
        domain=next(graph.objects(prop, RDFS.domain), None),
        range=next(graph.objects(prop, RDFS.range), None),
        surface_forms=_surface_forms(graph, prop),
    )


def load_ontology(path: Path | str = DEFAULT_ONTOLOGY_PATH) -> OntologySchema:
    """Legge il file .owl (in sintassi Turtle) e ne costruisce lo schema.

    È la funzione che TUTTI gli altri moduli chiamano per accedere
    all'ontologia. Passi:
      1. carica il grafo RDF dal file;
      2. trova tutte le classi (owl:Class);
      3. trova tutti gli individui (soggetti tipizzati con una classe);
      4. trova object property e data property.
    """
    graph = Graph()
    graph.parse(str(path), format="turtle")

    # (2) tutte le classi dichiarate come owl:Class
    classes: dict[URIRef, list[str]] = {}
    for cls in graph.subjects(RDF.type, OWL.Class):
        if isinstance(cls, URIRef):
            classes[cls] = _surface_forms(graph, cls)

    # (3) gli individui: qualsiasi cosa tipizzata con una delle nostre classi
    #     che non sia essa stessa una classe (es. Interval è un WorkoutType)
    individuals: dict[URIRef, list[str]] = {}
    for cls in classes:
        for ind in graph.subjects(RDF.type, cls):
            if isinstance(ind, URIRef) and ind not in classes:
                individuals[ind] = _surface_forms(graph, ind)

    # (4) le relazioni (object property) e gli attributi (data property)
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
    """Legge il file delle shape SHACL (il "cancello" dei vincoli) e lo
    restituisce come grafo, pronto per pyshacl."""
    graph = Graph()
    graph.parse(str(path), format="turtle")
    return graph
