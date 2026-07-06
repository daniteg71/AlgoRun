# =============================================================================
# COSA FA QUESTO FILE
# -----------------------------------------------------------------------------
# Contiene i TEMPLATE di frasi (scritti da un LLM) usati per generare il
# dataset sintetico. Ogni template è una frase con dei "buchi" ({runner},
# {wtype}, ...) che il generatore (generator.py) riempie con le parole prese
# dall'ontologia, più la lista delle triple GOLD (le risposte corrette) che
# quella frase esprime.
#
# I 4 LIVELLI DI COMPLESSITÀ (Block 14) — servono a testare l'NLP in
# condizioni via via più difficili:
#   1. explicit      — trigger diretto, una frase semplice ("targets").
#   2. implicit      — serve capire un sinonimo ("aims for" invece di "targets").
#   3. long_distance — le entità sono lontane, separate da tante parole.
#   4. nested        — frase densa con più triple sovrapposte e ambigue.
#
# I "buchi" disponibili:
#   {runner}=nome corridore   {wtype}=tipo allenamento   {phase}=fase
#   {zone}=stato di sforzo     {song}=titolo canzone      {genre}=genere
#   {playlist}=nome playlist   {hr}=battito               {cad}=cadenza
#
# Ogni template elenca le sue ``triples`` come (slot_soggetto, nome_relazione,
# slot_oggetto): così il generatore sa le risposte corrette SENZA fare NLP.
# =============================================================================

TEMPLATES = {
    "explicit": [
        {
            "text": "{runner} performs a {wtype} session in the park.",
            "triples": [("runner", "performsSession", "session_implicit"),
                        ("session_implicit", "hasWorkoutType", "wtype")],
        },
        {
            "text": "The session records a heart rate of {hr} bpm.",
            "triples": [("session_implicit", "recordsReading", "hr_reading")],
        },
        {
            "text": "The heart rate reading reaches {zone} during the effort.",
            "triples": [("session_implicit", "hasEffortState", "zone")],
        },
        {
            "text": "The song {song} suits the {phase} phase.",
            "triples": [("song", "suitsPhase", "phase")],
        },
        {
            "text": "{song} matches {zone} perfectly.",
            "triples": [("song", "matchesEffort", "zone")],
        },
        {
            "text": "The track {song} belongs to genre {genre}.",
            "triples": [("song", "hasGenre", "genre")],
        },
        {
            "text": "{song} is added to the playlist {playlist}.",
            "triples": [("song", "includedIn", "playlist")],
        },
        {
            "text": "The playlist {playlist} is built for the {wtype} session.",
            "triples": [("playlist", "builtForSession", "session_implicit"),
                        ("session_implicit", "hasWorkoutType", "wtype")],
        },
        {
            "text": "The {phase} phase targets {zone}.",
            "triples": [("phase", "targetsEffort", "zone")],
        },
        {
            "text": "The session includes a {phase} phase.",
            "triples": [("session_implicit", "hasPhase", "phase")],
        },
    ],
    "implicit": [
        {
            # "completes"/"does" al posto di "performs"; sinonimo di allenamento
            "text": "{runner} completes a tough {wtype} before breakfast.",
            "triples": [("runner", "performsSession", "session_implicit"),
                        ("session_implicit", "hasWorkoutType", "wtype")],
        },
        {
            # "pulse" = battito (sinonimo), sforzo espresso senza dire "reading"
            "text": "Halfway through, the pulse of {runner} climbs into {zone}.",
            "triples": [("session_implicit", "hasEffortState", "zone")],
        },
        {
            # "fits" al posto di "suits"
            "text": "{song} really fits a {phase}, with its steady groove.",
            "triples": [("song", "suitsPhase", "phase")],
        },
        {
            # "queued in" al posto di "included in"
            "text": "The tune {song} gets queued in {playlist} for tomorrow.",
            "triples": [("song", "includedIn", "playlist")],
        },
        {
            # "logs" al posto di "records"
            "text": "The watch logs a beat of {hr} for this run.",
            "triples": [("session_implicit", "recordsReading", "hr_reading")],
        },
        {
            # "tailored to" al posto di "built for"
            "text": "{playlist} feels tailored to an intense {wtype}.",
            "triples": [("playlist", "builtForSession", "session_implicit"),
                        ("session_implicit", "hasWorkoutType", "wtype")],
        },
        {
            # genere indicato da una parola di stile
            "text": "With its unmistakable style, {song} is pure {genre}.",
            "triples": [("song", "hasGenre", "genre")],
        },
        {
            # "aims for" al posto di "targets"
            "text": "Every {phase} aims for {zone}, coach says.",
            "triples": [("phase", "targetsEffort", "zone")],
        },
    ],
    "long_distance": [
        {
            "text": ("{runner} laced up early this morning, checked the weather "
                     "twice, stretched for ten minutes, and finally performed "
                     "the {wtype} session that the coach had planned."),
            "triples": [("runner", "performsSession", "session_implicit"),
                        ("session_implicit", "hasWorkoutType", "wtype")],
        },
        {
            "text": ("The session started slowly along the river; after the "
                     "second kilometre, when the legs finally felt warm, the "
                     "watch recorded a heart rate that settled around {hr} bpm, "
                     "which put the reading squarely in {zone}."),
            "triples": [("session_implicit", "recordsReading", "hr_reading"),
                        ("session_implicit", "hasEffortState", "zone")],
        },
        {
            "text": ("{song} came on just as the rain started. Nobody at the "
                     "club could explain why, but everyone agreed that after "
                     "all these years the track still suits the {phase} phase "
                     "better than anything else."),
            "triples": [("song", "suitsPhase", "phase")],
        },
        {
            "text": ("The playlist {playlist} took weeks to assemble. Between "
                     "arguments about tempo and endless swapping of tracks, it "
                     "was eventually built for the {wtype} session scheduled "
                     "on Sunday."),
            "triples": [("playlist", "builtForSession", "session_implicit"),
                        ("session_implicit", "hasWorkoutType", "wtype")],
        },
        {
            "text": ("First came the warm-up, then a long stretch of silence, "
                     "then doubt; but {song}, an old favourite from a dusty "
                     "record shop, is filed by every streaming service under "
                     "{genre}, and it saved the run."),
            "triples": [("song", "hasGenre", "genre")],
        },
    ],
    "nested": [
        {
            "text": ("{runner} performs a {wtype} session that records a heart "
                     "rate of {hr} bpm reaching {zone}, while {song} — a "
                     "{genre} track queued in {playlist} — matches {zone} and "
                     "suits the {phase} phase."),
            "triples": [("runner", "performsSession", "session_implicit"),
                        ("session_implicit", "hasWorkoutType", "wtype"),
                        ("session_implicit", "recordsReading", "hr_reading"),
                        ("session_implicit", "hasEffortState", "zone"),
                        ("song", "hasGenre", "genre"),
                        ("song", "includedIn", "playlist"),
                        ("song", "matchesEffort", "zone"),
                        ("song", "suitsPhase", "phase")],
        },
        {
            "text": ("The playlist {playlist}, built for the {wtype} session "
                     "of {runner}, contains {song}, which belongs to {genre} "
                     "and suits the {phase} phase that targets {zone}."),
            "triples": [("playlist", "builtForSession", "session_implicit"),
                        ("session_implicit", "hasWorkoutType", "wtype"),
                        ("runner", "performsSession", "session_implicit"),
                        ("playlist", "containsSong", "song"),
                        ("song", "hasGenre", "genre"),
                        ("song", "suitsPhase", "phase"),
                        ("phase", "targetsEffort", "zone")],
        },
        {
            "text": ("During the {phase} phase, which targets {zone}, the "
                     "session records a cadence of {cad} spm while {song} "
                     "plays from {playlist}; the track matches {zone} and the "
                     "session has a {phase} phase indeed."),
            "triples": [("phase", "targetsEffort", "zone"),
                        ("session_implicit", "recordsReading", "cad_reading"),
                        ("song", "includedIn", "playlist"),
                        ("song", "matchesEffort", "zone"),
                        ("session_implicit", "hasPhase", "phase")],
        },
    ],
}

# Entity pools for slots that are NOT ontology individuals. Song titles,
# artists, playlist and runner names are fictional (LLM-invented) to avoid
# any copyright/real-data issue; genres use common genre words that the
# music catalog (M5) also contains.
RUNNER_NAMES = ["Danny", "Giulia", "Marco", "Sara", "Luca", "Elena", "Paolo", "Anna"]
SONG_TITLES = [
    "Midnight Stride", "Concrete Sky", "Neon Pulse", "Silver Lungs",
    "Gravity Falls Apart", "Kilometre Zero", "Heartbeat Avenue",
    "Tempo Ghost", "Marathon Moon", "Static Sunrise", "Iron Cadence",
    "Blue Asphalt", "Runner's High", "Echo Sprint", "Final Interval",
]
GENRES = ["techno", "rock", "hip hop", "drum and bass", "house", "pop", "metal", "ambient"]
PLAYLIST_NAMES = [
    "Morning Push", "Race Day", "Easy Miles", "Threshold Thunder",
    "Sunday Long", "Recovery Waves", "Interval Inferno",
]
HR_VALUES = ["132", "145", "151", "158", "164", "172", "181", "189"]
CADENCE_VALUES = ["158", "164", "170", "176", "182"]
