# =============================================================================
# COSA FA QUESTO FILE
# -----------------------------------------------------------------------------
# Strumenti di VALUTAZIONE dell'ontologia (deliverable del corso, Block 13).
# Due cose:
#
#   1. check_consistency() -> lancia un reasoner logico (HermiT) sull'ontologia
#      (+ eventuali dati) e dice se è CONSISTENTE, cioè priva di contraddizioni.
#      È la prova che gli assiomi di disgiunzione "mordono" davvero: se un
#      individuo viene dichiarato sia Agent sia Process (che sono disgiunti),
#      il reasoner segnala l'inconsistenza.
#
#   2. sample_kg() -> costruisce un piccolo grafo di ESEMPIO valido (una
#      sessione completa: runner, fasi, letture, canzoni, playlist). Serve da
#      "banco di prova" per le competency question (le domande a cui l'ontologia
#      deve saper rispondere, vedi tests/test_competency_questions.py).
#
# Reasoner (HermiT) e SHACL fanno due lavori diversi: il reasoner controlla che
# lo SCHEMA sia coerente; SHACL respinge i singoli DATI sbagliati.
# =============================================================================

from __future__ import annotations

import tempfile
from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, XSD

from .loader import AR, DEFAULT_ONTOLOGY_PATH, load_ontology

# prefisso per i DATI di esempio (istanze), distinto da AR (lo schema)
EX = Namespace("http://algorun.org/data#")


def check_consistency(abox: Graph | None = None) -> bool:
    """Ritorna True se l'ontologia (+ dati opzionali) è logicamente consistente.

    Usa owlready2 + il reasoner HermiT. owlready2 legge bene solo RDF/XML,
    quindi si scrive il grafo unito in un file temporaneo, lo si carica e si
    lancia il reasoner: se trova una contraddizione solleva un'eccezione.
    """
    import owlready2

    # unisce lo schema (ontologia) con gli eventuali dati da controllare
    graph = load_ontology().graph
    if abox is not None:
        graph = graph + abox

    # HermiT vuole un file su disco: lo scriviamo in RDF/XML (formato "xml")
    with tempfile.NamedTemporaryFile("w", suffix=".owl", delete=False,
                                     encoding="utf-8") as fh:
        fh.write(graph.serialize(format="xml"))
        tmp_path = fh.name

    world = owlready2.World()                       # "mondo" isolato di owlready2
    world.get_ontology(f"file://{tmp_path}").load()
    try:
        with world.get_ontology("http://algorun.org/reasoning"):
            owlready2.sync_reasoner(world, debug=0)  # <-- qui gira HermiT
        return True                                  # nessuna eccezione = consistente
    except owlready2.OwlReadyInconsistentOntologyError:
        return False                                 # contraddizione trovata
    finally:
        Path(tmp_path).unlink(missing_ok=True)       # pulizia del file temporaneo


def sample_kg() -> Graph:
    """Costruisce un piccolo grafo di esempio VALIDO che esercita ogni
    competency question.

    Scenario: un runner (danny) che preferisce la techno, fa una sessione di
    tipo Interval con due fasi ordinate (warmup -> sprint), registra battito e
    cadenza, ha uno stato di sforzo, e ha una playlist con due canzoni.
    """
    g = Graph()
    g.bind("ar", AR)
    g.bind("ex", EX)

    # scorciatoia per scrivere un numero decimale in RDF
    def dec(v: str) -> Literal:
        return Literal(v, datatype=XSD.decimal)

    # --- runner + preferenza musicale ---
    g.add((EX.danny, RDF.type, AR.Runner))
    g.add((EX.techno, RDF.type, AR.Genre))
    g.add((EX.rock, RDF.type, AR.Genre))
    g.add((EX.danny, AR.prefersGenre, EX.techno))

    # --- la sessione, di tipo Interval, eseguita da danny ---
    g.add((EX.session1, RDF.type, AR.WorkoutSession))
    g.add((EX.danny, AR.performsSession, EX.session1))
    g.add((EX.session1, AR.hasWorkoutType, AR.Interval))
    g.add((EX.session1, AR.durationMinutes, dec("40")))

    # --- due fasi in ordine (warm -> sprint), ognuna col suo sforzo bersaglio ---
    g.add((EX.warm, RDF.type, AR.TrainingPhase))
    g.add((EX.sprint, RDF.type, AR.TrainingPhase))
    g.add((EX.session1, AR.hasPhase, EX.warm))
    g.add((EX.session1, AR.hasPhase, EX.sprint))
    g.add((EX.warm, AR.nextPhase, EX.sprint))
    g.add((EX.warm, AR.targetsEffort, AR.LowEffort))
    g.add((EX.sprint, AR.targetsEffort, AR.VeryHighEffort))

    # --- stato di sforzo e andamento attuali della sessione ---
    g.add((EX.session1, AR.hasEffortState, AR.VeryHighEffort))
    g.add((EX.session1, AR.hasTrend, AR.Increasing))

    # --- letture dei sensori (battito + cadenza) ---
    g.add((EX.hr1, RDF.type, AR.HeartRateReading))
    g.add((EX.session1, AR.recordsReading, EX.hr1))
    g.add((EX.hr1, AR.heartRateBpm, dec("185")))
    g.add((EX.cad1, RDF.type, AR.CadenceReading))
    g.add((EX.session1, AR.recordsReading, EX.cad1))
    g.add((EX.cad1, AR.cadenceSpm, dec("172")))

    # --- due canzoni con i loro attributi (bpm, genere, fase adatta, sforzo) ---
    g.add((EX.song_pulse, RDF.type, AR.Song))
    g.add((EX.song_pulse, AR.songTitle, Literal("Neon Pulse")))
    g.add((EX.song_pulse, AR.bpmValue, dec("172")))
    g.add((EX.song_pulse, AR.hasGenre, EX.techno))
    g.add((EX.song_pulse, AR.suitsPhase, EX.sprint))
    g.add((EX.song_pulse, AR.matchesEffort, AR.VeryHighEffort))

    g.add((EX.song_calm, RDF.type, AR.Song))
    g.add((EX.song_calm, AR.songTitle, Literal("Silver Lungs")))
    g.add((EX.song_calm, AR.bpmValue, dec("128")))
    g.add((EX.song_calm, AR.hasGenre, EX.rock))
    g.add((EX.song_calm, AR.suitsPhase, EX.warm))
    g.add((EX.song_calm, AR.matchesEffort, AR.LowEffort))

    # --- la playlist, costruita per la sessione, che contiene le due canzoni ---
    g.add((EX.pl1, RDF.type, AR.Playlist))
    g.add((EX.pl1, AR.builtForSession, EX.session1))
    g.add((EX.pl1, AR.containsSong, EX.song_pulse))
    g.add((EX.pl1, AR.containsSong, EX.song_calm))

    return g


def kg_with_ontology() -> Graph:
    """Unisce il grafo di esempio (i DATI) con l'ontologia (lo SCHEMA), così le
    query SPARQL possono anche navigare la gerarchia delle classi."""
    g = load_ontology().graph + sample_kg()
    return g
