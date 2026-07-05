"""Competency questions as SPARQL tests (Grüninger & Fox; course Block 12/13).

Each competency question is a requirement AND a test: the ontology is "done"
when every CQ returns the expected answer over the sample KG. This is the
functional evaluation of the ontology.
"""

from algorun.ontology.evaluation import kg_with_ontology
from algorun.ontology.loader import AR

PREFIX = """
PREFIX ar: <http://algorun.org/ontology#>
PREFIX ex: <http://algorun.org/data#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
"""


def _ask(query: str):
    return list(kg_with_ontology().query(PREFIX + query))


def test_cq1_songs_for_very_high_effort():
    rows = _ask("""SELECT ?song WHERE {
        ?song a ar:Song ; ar:matchesEffort ar:VeryHighEffort .
    }""")
    assert {str(r[0]).split("#")[-1] for r in rows} == {"song_pulse"}


def test_cq2_song_bpm_matching_cadence_172():
    rows = _ask("""SELECT ?song WHERE {
        ?song a ar:Song ; ar:bpmValue ?bpm . FILTER(?bpm = 172)
    }""")
    assert {str(r[0]).split("#")[-1] for r in rows} == {"song_pulse"}


def test_cq3_playlist_built_for_session():
    rows = _ask("""SELECT ?pl WHERE { ?pl ar:builtForSession ex:session1 }""")
    assert {str(r[0]).split("#")[-1] for r in rows} == {"pl1"}


def test_cq4_effort_state_of_session():
    rows = _ask("""SELECT ?e WHERE { ex:session1 ar:hasEffortState ?e }""")
    assert AR.VeryHighEffort in {r[0] for r in rows}


def test_cq5_preferred_genres_of_runner():
    rows = _ask("""SELECT ?g WHERE { ex:danny ar:prefersGenre ?g }""")
    assert {str(r[0]).split("#")[-1] for r in rows} == {"techno"}


def test_cq6_sessions_and_types_of_runner():
    rows = _ask("""SELECT ?s ?t WHERE {
        ex:danny ar:performsSession ?s . ?s ar:hasWorkoutType ?t .
    }""")
    assert any(str(r[1]).endswith("Interval") for r in rows)


def test_cq7_songs_matching_effort_and_preferred_genre():
    rows = _ask("""SELECT ?song WHERE {
        ex:danny ar:prefersGenre ?g .
        ?song a ar:Song ; ar:hasGenre ?g ; ar:matchesEffort ar:VeryHighEffort .
    }""")
    assert {str(r[0]).split("#")[-1] for r in rows} == {"song_pulse"}


def test_cq8_phase_sequence_and_target_effort():
    rows = _ask("""SELECT ?p1 ?p2 WHERE {
        ?p1 ar:nextPhase ?p2 ; ar:targetsEffort ?e1 .
        ?p2 ar:targetsEffort ?e2 .
    }""")
    assert len(rows) == 1
    p1, p2 = rows[0]
    assert str(p1).endswith("warm") and str(p2).endswith("sprint")


def test_cq9_readings_recorded_in_session():
    rows = _ask("""SELECT ?r WHERE { ex:session1 ar:recordsReading ?r }""")
    assert len(rows) == 2  # HR + cadence


def test_cq10_effort_prescribes_acoustic_target():
    """Reasoning chain phase -> targetsEffort -> effort -> prescribesTarget."""
    rows = _ask("""SELECT ?bpmMin ?bpmMax WHERE {
        ex:sprint ar:targetsEffort ?effort .
        ?effort ar:prescribesTarget ?t .
        ?t ar:targetBpmMin ?bpmMin ; ar:targetBpmMax ?bpmMax .
    }""")
    assert len(rows) == 1
    # sprint -> VeryHighEffort -> IntervalTarget (150-180)
    assert int(rows[0][0]) == 150 and int(rows[0][1]) == 180
