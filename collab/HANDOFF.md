# HANDOFF.md — Two-Person / Two-AI Coordination Log

> **Protocol (read me first).** This project is built by two teammates, each
> working with their own AI assistant. Whoever starts a work session (human or
> AI, any tool — Claude, ChatGPT, Gemini, ...) MUST:
>
> 1. **Read this file FIRST** and report to their user the pending TODOs,
>    ideas and open questions left by the other teammate (newest entries
>    below the header, most recent first).
> 2. At the **end** of the session, **prepend a new entry** right below this
>    header using the template, and commit it with the session's work.
>
> Never rewrite or delete previous entries (append-only history). Keep entries
> honest: unfinished work is listed as unfinished.

## Entry template

```markdown
---
### [YYYY-MM-DD HH:MM] — <author> (with <AI tool>)
**What I did:** ...
**Ideas that came up:** ...
**TODOs for the other teammate:** ...
**Open questions:** ...
```

<!-- NEW ENTRIES GO DIRECTLY BELOW THIS LINE -->

---
### [2026-07-03 19:30] — Danny (with Claude Code)
**What I did:**
- **M2 complete.** `src/algorun/datagen/`: LLM-authored sentence templates
  for the 4 complexity tiers (`templates.py`), generator that instantiates
  them with surface forms drawn from the ontology label dictionary and
  computes gold annotations (entity spans + triples) automatically
  (`generator.py`), dataset validation script (`validate.py`).
- Generated `data/synthetic/{train,val,test}.jsonl`: 800 records, exact
  70/15/15 split, perfectly tier-balanced (140/30/30 per tier per split).
  Committed to git — it is a course deliverable.
- Package now installs editable (`pip install -e .`); 17 tests green.

**Ideas that came up:**
- Implicit-tier records draw surface forms from skos:altLabel only (e.g.,
  "pulse" for heart rate, "HIIT" for interval) — synonym resolution is thus
  guaranteed to be required, matching the tier definition.
- Implicit graph nodes (the session, the readings) get `mentioned: false`
  entities with no text span — the extraction pipeline will have to mint
  those nodes per record. Keep this convention in mind for M3.

**TODOs for the other teammate:**
- Read a few records of each tier in `data/synthetic/train.jsonl` and sanity
  check the English + the annotations.
- If you want more lexical variety, add templates to `templates.py` and
  regenerate (`python -m algorun.datagen.generator`) — seed is fixed so
  results stay reproducible.
- Still pending: Sensor Logger recordings, Kaggle Spotify dataset, Python
  3.11 decision.

**Open questions:**
- 200 records/tier enough for fine-tuning the M4 validator? We can bump
  `--per-tier` cheaply if needed.

---
### [2026-07-03 19:00] — Danny (with Claude Code)
**What I did:**
- **M1 complete.** Built `ontology/algorun.owl` (Turtle/OWL): hierarchical
  classes (Runner, WorkoutSession, WorkoutType, TrainingPhase, SensorReading
  subclasses, IntensityZone Z1–Z5, Song/Genre/Playlist), 14 object properties
  with explicit domain/range + inverses, 13 data properties, rdfs:label +
  skos:altLabel synonyms on everything (they feed the rule-based NER
  dictionary and the implicit complexity tier).
- Built `ontology/shapes.ttl`: SHACL shapes mirroring every domain/range pair
  plus value-range constraints (HR ∈ [25,240], energy ∈ [0,1], ...).
- `src/algorun/ontology/loader.py`: parses the OWL into an OntologySchema,
  builds the longest-match-first label dictionary and the relation trigger
  dictionary.
- 10 pytest tests, all green (`python -m pytest`).

**Ideas that came up:**
- **Important theory point for the report:** with RDFS inference enabled,
  rdfs:domain/range *classify* subjects instead of rejecting them (a Playlist
  "performing" a session just gets inferred to be a Runner!). SHACL validation
  must run with inference OFF — this concretely demonstrates WHY the course
  mandates SHACL as the constraint gate. Great paragraph for the report.
- pyshacl quirk: `ont_graph` is ignored when inference="none"; merge the
  ontology into the data graph manually.

**TODOs for the other teammate:**
- Still pending from last entry: Sensor Logger recordings + Kaggle Spotify
  dataset download.
- My Mac only has Python 3.9 — fine up to M3, but for M4 fine-tuning let's
  decide: brew-install Python 3.11 locally or train on Colab. Your setup?

**Open questions:**
- Do we want genre preferences of the runner in the ontology (e.g.,
  `prefersGenre(Runner→Genre)`)? I left it out for now (YAGNI) but it would
  enable personalisation in M5.

---
### [2026-07-03 18:30] — Danny (with Claude Code)
**What I did:**
- Read the full course Project Description (Block 14) and distilled the
  binding rules into `GUIDELINES.md`.
- Approved the overall architecture: sensor data (Sensor Logger) → NL
  narratives → ontology-grounded NLP pipeline → RDF Knowledge Graph → SPARQL
  playlist recommender; direct structured mapping of the same sensor sessions
  provides ground-truth triples for benchmarking.
- Scaffolded the repository: directory tree, `CLAUDE.md` (AI session
  protocol), `GUIDELINES.md` (course rules), this handoff log,
  `requirements.txt`, `README.md` with the milestone plan (M0–M6).

**Ideas that came up:**
- Song BPM ≈ target cadence (or half-time) as the core matching heuristic;
  energy scales with intensity zone; phase sequencing maps to a BPM curve
  (warm-up ramps up, cool-down ramps down).
- Use the direct sensor→triples mapping as ground truth so the NLP pipeline
  can be scored on real sessions too, not only on synthetic data.
- Personal Spotify playlist is matched offline (title+artist fuzzy join
  against the Kaggle tracks dataset) because the Spotify audio-features API
  is deprecated.

**TODOs for the other teammate:**
- Install **Sensor Logger** (+ watch companion if you have a smartwatch) and
  record 2–3 real runs: enable Location, Accelerometer, Gravity, Barometer,
  Heart Rate; export as CSV (zip) and drop them into `data/sensor/`.
- Download the Kaggle "Spotify Tracks Dataset" (with tempo/energy/valence
  columns) into `data/music/`.
- Review `GUIDELINES.md` and the milestone plan in `README.md` — flag
  anything you disagree with here.

**Open questions:**
- Which LLM do we use for synthetic data generation (M2)? Proposal: Claude via
  API or manual prompting, output checked by the dataset validation script.
- Do we both have GPU access for M4 fine-tuning, or should we plan for Google
  Colab?
