"""Ontology evaluation helpers (course Block 13 deliverable).

Two checks used by the test suite and by `report/ontology_eval.md`:

- ``check_consistency`` runs an OWL DL reasoner (HermiT via owlready2) over the
  ontology plus an optional ABox and reports whether the model is consistent.
  This is what proves the disjointness axioms actually bite: an individual
  typed as two disjoint cores makes the ontology inconsistent.

- ``sample_kg`` builds a small, valid ABox used to answer the competency
  questions (see tests/test_competency_questions.py). Keeping it here means
  the fixture is defined once and reused.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, XSD

from .loader import AR, DEFAULT_ONTOLOGY_PATH, load_ontology

EX = Namespace("http://algorun.org/data#")


def check_consistency(abox: Graph | None = None) -> bool:
    """Return True iff ontology (+ optional ABox) is logically consistent.

    Uses owlready2 + HermiT. The ontology and data are merged into one Turtle
    file that owlready2 loads, then ``sync_reasoner`` raises if inconsistent.
    """
    import owlready2

    graph = load_ontology().graph
    if abox is not None:
        graph = graph + abox

    with tempfile.NamedTemporaryFile("w", suffix=".owl", delete=False,
                                     encoding="utf-8") as fh:
        # owlready2 reads RDF/XML reliably; serialize the merged graph to it
        fh.write(graph.serialize(format="xml"))
        tmp_path = fh.name

    world = owlready2.World()
    world.get_ontology(f"file://{tmp_path}").load()
    try:
        with world.get_ontology("http://algorun.org/reasoning"):
            owlready2.sync_reasoner(world, debug=0)
        return True
    except owlready2.OwlReadyInconsistentOntologyError:
        return False
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def sample_kg() -> Graph:
    """A small valid ABox exercising every competency question.

    One runner, one interval session with two ordered phases, HR/cadence
    readings, effort states, a genre preference, two songs, and a playlist
    built for the session.
    """
    g = Graph()
    g.bind("ar", AR)
    g.bind("ex", EX)

    def dec(v: str) -> Literal:
        return Literal(v, datatype=XSD.decimal)

    # runner + preference
    g.add((EX.danny, RDF.type, AR.Runner))
    g.add((EX.techno, RDF.type, AR.Genre))
    g.add((EX.rock, RDF.type, AR.Genre))
    g.add((EX.danny, AR.prefersGenre, EX.techno))

    # session of type Interval
    g.add((EX.session1, RDF.type, AR.WorkoutSession))
    g.add((EX.danny, AR.performsSession, EX.session1))
    g.add((EX.session1, AR.hasWorkoutType, AR.Interval))
    g.add((EX.session1, AR.durationMinutes, dec("40")))

    # two ordered phases
    g.add((EX.warm, RDF.type, AR.TrainingPhase))
    g.add((EX.sprint, RDF.type, AR.TrainingPhase))
    g.add((EX.session1, AR.hasPhase, EX.warm))
    g.add((EX.session1, AR.hasPhase, EX.sprint))
    g.add((EX.warm, AR.nextPhase, EX.sprint))
    g.add((EX.warm, AR.targetsEffort, AR.LowEffort))
    g.add((EX.sprint, AR.targetsEffort, AR.VeryHighEffort))

    # current effort + trend
    g.add((EX.session1, AR.hasEffortState, AR.VeryHighEffort))
    g.add((EX.session1, AR.hasTrend, AR.Increasing))

    # readings
    g.add((EX.hr1, RDF.type, AR.HeartRateReading))
    g.add((EX.session1, AR.recordsReading, EX.hr1))
    g.add((EX.hr1, AR.heartRateBpm, dec("185")))
    g.add((EX.cad1, RDF.type, AR.CadenceReading))
    g.add((EX.session1, AR.recordsReading, EX.cad1))
    g.add((EX.cad1, AR.cadenceSpm, dec("172")))

    # songs
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

    # playlist
    g.add((EX.pl1, RDF.type, AR.Playlist))
    g.add((EX.pl1, AR.builtForSession, EX.session1))
    g.add((EX.pl1, AR.containsSong, EX.song_pulse))
    g.add((EX.pl1, AR.containsSong, EX.song_calm))

    return g


def kg_with_ontology() -> Graph:
    """Sample ABox merged with the TBox, ready for SPARQL over class hierarchy."""
    g = load_ontology().graph + sample_kg()
    return g
