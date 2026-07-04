"""Competency questions as SPARQL tests (Grüninger & Fox; course Block 12/13).

Each CQ from report/ontology_design.md is a requirement AND a test: the
ontology is "done" when every CQ returns the expected answer over the sample
KG. This is the functional evaluation of the ontology.
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


def test_cq1_songs_for_sprint_phase_in_z5():
    rows = _ask("""SELECT ?song WHERE {
        ?song a ar:Song ; ar:suitsPhase ?ph ; ar:matchesZone ar:Z5 .
        ?ph ar:targetsZone ar:Z5 .
    }""")
    songs = {str(r[0]).split("#")[-1] for r in rows}
    assert songs == {"song_pulse"}


def test_cq2_song_bpm_matching_cadence_172():
    rows = _ask("""SELECT ?song ?bpm WHERE {
        ?song a ar:Song ; ar:bpmValue ?bpm .
        FILTER(?bpm = 172)
    }""")
    assert {str(r[0]).split("#")[-1] for r in rows} == {"song_pulse"}


def test_cq3_playlist_built_for_session():
    rows = _ask("""SELECT ?pl WHERE { ?pl ar:builtForSession ex:session1 }""")
    assert {str(r[0]).split("#")[-1] for r in rows} == {"pl1"}


def test_cq4_zone_of_heart_rate_in_session():
    rows = _ask("""SELECT ?zone WHERE {
        ex:session1 ar:recordsReading ?hr .
        ?hr a ar:HeartRateReading ; ar:readingInZone ?zone .
    }""")
    assert AR.Z5 in {r[0] for r in rows}


def test_cq5_preferred_genres_of_runner():
    rows = _ask("""SELECT ?g WHERE { ex:danny ar:prefersGenre ?g }""")
    assert {str(r[0]).split("#")[-1] for r in rows} == {"techno"}


def test_cq6_sessions_and_types_of_runner():
    rows = _ask("""SELECT ?s ?t WHERE {
        ex:danny ar:performsSession ?s . ?s ar:hasWorkoutType ?t .
    }""")
    assert (any(str(r[1]).endswith("Interval") for r in rows))


def test_cq7_songs_matching_zone_and_preferred_genre():
    rows = _ask("""SELECT ?song WHERE {
        ex:danny ar:prefersGenre ?g .
        ?song a ar:Song ; ar:hasGenre ?g ; ar:matchesZone ar:Z5 .
    }""")
    assert {str(r[0]).split("#")[-1] for r in rows} == {"song_pulse"}


def test_cq8_phase_sequence_and_targets():
    rows = _ask("""SELECT ?p1 ?p2 ?z1 ?z2 WHERE {
        ?p1 ar:nextPhase ?p2 ; ar:targetsZone ?z1 .
        ?p2 ar:targetsZone ?z2 .
    }""")
    assert len(rows) == 1
    p1, p2, z1, z2 = rows[0]
    assert str(p1).endswith("warm") and str(p2).endswith("sprint")


def test_cq9_readings_recorded_in_session():
    rows = _ask("""SELECT ?r WHERE { ex:session1 ar:recordsReading ?r }""")
    assert len(rows) == 2  # HR + cadence


def test_cq10_bpm_curve_for_session_phases():
    # BPM of the song suited to each phase, ordered by the phase sequence
    rows = _ask("""SELECT ?song ?bpm WHERE {
        ex:warm ar:nextPhase ?next .
        ?song ar:suitsPhase ex:warm ; ar:bpmValue ?bpm .
    }""")
    assert any(float(r[1]) == 128 for r in rows)


def test_zone_prescribes_acoustic_target():
    """The reasoning chain phase → zone → acoustic target (BPM band)."""
    rows = _ask("""SELECT ?bpmMin ?bpmMax WHERE {
        ex:sprint ar:targetsZone ?zone .
        ?zone ar:prescribesTarget ?t .
        ?t ar:targetBpmMin ?bpmMin ; ar:targetBpmMax ?bpmMax .
    }""")
    assert len(rows) == 1
    # sprint → Z5 → IntervalTarget (150–180)
    assert int(rows[0][0]) == 150 and int(rows[0][1]) == 180
