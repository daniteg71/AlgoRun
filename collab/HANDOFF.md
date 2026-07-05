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
### [2026-07-05 12:30] — Danny (with Claude Code)
**What I did:**
- **Integrated the teammate's sensor/BPM pipeline** into `src/algorun/sensors/`
  (added **as-is**): `physiological_state.py` (window → HRR/effort/trend),
  `generate_simulated_bpm.py` (synthetic BPM, seed 42), `build_dataset.py`
  (30 s / 5 s sliding windows). Both verified end-to-end; generated CSVs
  git-ignored. Fixed a stray tracked `data/simulated` file.

**TODOs for the other teammate (alignment — did NOT change your code):**
- `build_dataset.py` import → package-relative for `import`-based use.
- Map the 4 effort states to the ontology's 5 zones (Z1–Z5).
- Map workout goals `easy/moderate/interval` → `Recovery/Endurance/Tempo/
  Interval/LongRun`.

**Open questions:** 30 s window (offline) vs 10 s (live) — unify or keep both?

---
### [2026-07-04 18:30] — Danny (with Claude Code)
**What I did:**
- **Sensor scope narrowed to two sensors only** (per Danny's decision):
  accelerometer → cadence, and heart-rate sensor → beats. Removed
  `PaceReading` + `ElevationReading` classes, their data properties
  (`paceMinPerKm`, `elevationMeters`), `distanceKm` (GPS-dependent), and the
  `PaceShape`. Reading-types disjointness now covers HR + cadence. 41 tests
  still green, ontology still consistent.
- **`report/ontology_criteria.md`** — the full step-by-step criteria for
  building/judging the ontology (10 steps + acceptance checklist): scope,
  competency questions, reuse, disjoint cores, taxonomy/relation/attribute
  criteria, SKOS, SHACL, 3-level validation, naming hygiene.

**Ideas that came up:**
- Best way to *see* the ontology visually (answered to Danny): Protégé's
  **OntoGraf** and **OWLViz** tabs for interactive graphs; **WebVOWL**
  (webvowl.dev) for a polished VOWL diagram to drop into the presentation.

**TODOs for the other teammate:**
- If you still want distance/elevation for LongRun stats, say so — I removed
  them because we dropped GPS/barometer; easy to re-add.

**Open questions:** none.

---
### [2026-07-04 17:30] — Danny (with Claude Code)
**What I did:**
- **Decided the panic-button threshold: 93% HRmax** (was proposed 95%).
  EmergencyPriority fires when smoothed HR ≥ 93% HRmax OR ≥ safeMaxHeartRateBpm.
  Updated `report/music_science.md` and `report/ontology_logic.md`.
  `safeMaxHeartRateBpm` defaults to 93% HRmax, overridable per runner.

**Open questions:** none new. The panic-button question below is now closed.

---
### [2026-07-04 17:00] — Danny (with Claude Code)
**What I did (on the v0.3 branch, extends PR #5):**
- **Reworked the acoustic-target taxonomy to 4 zone-indexed levels** matching
  the training-zone × music table: RecoveryTarget (Z1, 90–110, energy 0.1–0.3),
  EasyTarget (Z2, 120–130), ThresholdTarget (Z3–Z4, 130–150), IntervalTarget
  (Z5, 150–180). Targets are now prescribed by **IntensityZone**, not phase, so
  the reasoning chain is `phase → targetsZone → zone → prescribesTarget →
  target` (sensor-driven and plan-driven routes meet at the same target).
- **`report/ontology_logic.md`** — the full theory document you asked for:
  physiological-states modelling, the three-core backbone, the reasoning chain,
  the zone×music table, entrainment, the **1:1 vs half-time BPM-cadence trick**
  (why recovery is 90–110 not 160), arousal/dissociation, the tempo ceiling,
  and the full "when a song is too fast" safety logic.
- Updated `report/music_science.md` table + added the Google Scholar pointer
  ("Training Intensity Zones Music Synchronization") and practitioner guides.
- 41 tests green (new test for the zone→target chain).

**Ideas that came up:**
- The half-time ratio is the single most important idea to get across in the
  presentation: low intensity → optimize *arousal* (calm), high intensity →
  optimize *synchronization* (drive). It explains the whole BPM table.
- Note: I lowered the BPM bands vs my earlier v0.3 (was 120–180). The new
  numbers match your table and the practitioner literature better.

**TODOs for the other teammate:**
- Note about Protégé: our `algorun.owl` is hand-written Turtle but 100%
  Protégé-compatible. For the presentation, open it in Protégé and run the
  built-in HermiT reasoner to get screenshots (same consistency our tests
  already prove).
- Still open: panic-button threshold (below).

**Open questions:**
- Confirm `safeMaxHeartRateBpm` default = 95% HRmax (emergency line, ABOVE the
  Z5 training band). Or a fixed absolute BPM?

---
### [2026-07-04 15:00] — Danny (with Claude Code)
**What I did:**
- **Ontology v0.3 — health/music-science layer** (branch `ontology-v0.3-health`,
  built ON TOP of v0.2). Read Terry & Karageorghis (2011) "Chariots of Fire"
  and encoded the evidence:
  - `AcousticTarget` class = the target point (BPM/energy/valence + duration
    bounds) the reasoner produces, NOT a song → feeds the vector search.
  - Per-phase targets: recovery 120–140, tempo 150–160 (≥6 min, flow), peak
    170–180 (≤4 min, intervals).
  - `trackDurationMs` on Song + duration bounds on targets (the "haDurata"
    idea).
  - Runner health props: max/resting/safeMax heart rate (Tanaka/Karvonen).
  - `ActionPriority` (Normal/Emergency) for the dual-speed controller.
  - **3 SPARQL-SHACL safety constraints**: cadence jump ≤5%, no energetic
    target above safe-max HR, no energetic target under EmergencyPriority.
- `report/music_science.md`: full evidence doc — BPM table, cardiac benchmark
  models (Fox/Tanaka/Karvonen/5-zone), where to push vs. hold back, the
  hysteresis + playback-lock + panic-button control rules for M5.
- 40 tests green (6 new health-constraint tests). ALGORITHMS.md updated.

**Ideas that came up:**
- Honesty flagged in the report: 120–140 is the Karageorghis *motivational*
  band; 150–180 comes from cadence-*synchronization* studies. Two rationales,
  cited separately — don't overclaim.
- The ontology sets WHAT + HOW-URGENT; the M5 Python server owns WHEN
  (smoothing + lock + emergency bypass). Clean separation for the report.

**TODOs for the other teammate:**
- **Decide the panic-button threshold** (open question below).
- PRs are piling up unmerged: #2 (old design doc — close it), #3 (v0.2
  ontology), #4 (CLAUDE objective), and this v0.3 PR. Please merge in order
  #3 → #4 → v0.3 so `main` catches up.

**Open questions:**
- Panic-button trigger: proposed default is smoothed HR ≥ 95% HRmax OR ≥
  runner's safeMaxHeartRateBpm. Agree, or set a fixed BPM (e.g. 190)?

---
### [2026-07-04 12:00] — Danny (with Claude Code)
**What I did:**
- **Ontology v0.2** (branch `ontology-v0.2`, PR open). Followed the Block 12
  method:
  - Three disjoint IOF-style cores: Agent / Process / InformationEntity
    (`owl:disjointWith`). Reading types and Song/Genre/Playlist also disjoint.
  - Completed all forward/inverse property pairs (was 4/14, now all).
  - New `prefersGenre (Runner→Genre)` + SHACL shape (enables personalisation).
  - SKOS layer: WorkoutType and Genre are now `skos:Concept` in concept
    schemes (double-typed, so the NER dictionary is unchanged).
  - Light **standard alignment** (no imports, just axioms): SensorReading ⊑
    sosa:Observation, phases ↔ OWL-Time, BPM ↔ Music Ontology.
- **Formal evaluation** (Block 13 deliverable): 10 competency questions as
  SPARQL tests, reasoner consistency check (HermiT via owlready2 — a
  disjoint-core violation is proven inconsistent), OOPS!/OntoClean write-up
  in `report/ontology_eval.md`.
- 34 tests green. ALGORITHMS.md + this handoff updated. Design doc recovered
  from PR #2 into `report/ontology_design.md`.

**Ideas that came up:**
- The reasoner check and the SHACL gate are the two halves of the same idea:
  reasoner proves the *schema* is coherent (open world), SHACL rejects *bad
  data* (closed world). Strong slide for the presentation.
- SOSA/SSN maps 1:1 onto our sensor side — worth a dedicated slide.

**TODOs for the other teammate:**
- Run `ontology/algorun.owl` through OOPS! (https://oops.linkeddata.es/) and
  paste the result into `report/ontology_eval.md` §3.
- Reasoner needs Java — check you have it (`java -version`) before running
  the ontology tests.
- PR #2 (old design-doc branch) is now superseded by this PR — close it.

**Open questions:**
- Add `nextPhase` chains to the sample KG for longer BPM-curve CQs, or keep
  the fixture minimal? I kept it minimal for now.

---
### [2026-07-03 20:00] — Danny (with Claude Code)
**What I did:**
- **New collaboration rules** (now in `CLAUDE.md` + `GUIDELINES.md` Rules 6–8):
  1. Session start = `git pull`, always, for both of us.
  2. After every medium-or-larger task: update the communication files,
     commit on a feature branch, open a PR — no direct commits to `main`.
  3. Merge conflicts: the more reliable version wins (stronger rationale:
     green tests, guideline compliance, cited source); resolution documented
     here in HANDOFF.
  4. Code style is binding: essential, zero pomposity, symmetric interfaces,
     class-taught algorithms first.
- Created `ALGORITHMS.md`: provenance ledger (algorithm + exact variant +
  location + source/paper), already back-filled for M0–M2 and pre-filled
  with planned M3–M5 entries. It feeds the final presentation.

**Ideas that came up:**
- Final deliverable = code + presentation; the ledger doubles as the
  presentation outline (esp. the SHACL-vs-RDFS finding).

**TODOs for the other teammate:**
- Install the GitHub CLI (`brew install gh && gh auth login`) so PRs can be
  opened automatically from the terminal.
- Adopt the new workflow from your next session: pull → read HANDOFF → work
  on a feature branch → PR.

**Open questions:**
- Branch naming: I propose `m<N>-<short-name>` for milestones,
  `fix-<short-name>` for fixes. OK?

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
