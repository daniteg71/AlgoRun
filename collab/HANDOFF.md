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
### [2026-07-06 03:00] — Danny (with Claude Code)
**What I did:** **M4 — validator DistilBERT** (`src/algorun/validator.py`).
Prima una verifica onesta: il generatore trigger-based produceva SOLO
candidati giusti (0 negativi) → un validator sopra non avrebbe avuto senso.
Soluzione dal corso stesso (Architecture A): generatore **pairwise puro**
(tutte le coppie domain/range-compatibili, senza trigger) → 502 pos/2080 neg
su train, ceiling recall 0.39. Poi fine-tuning DistilBERT (frase, candidato
verbalizzato) → VALID/INVALID: 3 epoche su MPS (~2 min), val accuracy 0.99.

**Risultato sul test set (mai visto): baseline F1 0.24 → validator F1 0.48.**
Per tier: long_distance 0.00→0.47 (il modello legge tutta la frase, niente
finestra di token), implicit 0.16→0.57, explicit 0.42→0.58, nested 0.27→0.44.
Precision 1.00→0.90 (prezzo piccolo per +138% di recall). Questo È il
confronto Rule 4 baseline-vs-Transformer, con numeri veri.

Comandi: `python -m algorun.validator train` (ri-allena, modello in models/,
fuori git) e `python -m algorun.validator eval` (stampa il confronto).
73 test verdi (4 nuovi; l'inferenza si salta se il modello non c'è).

**TODOs for the other teammate:** allena il modello anche tu (train, ~2 min
con GPU Apple) così hai models/ in locale; se vuoi contribuire il confronto
RoBERTa (stesso script, MODEL_NAME diverso) è il prossimo passo naturale.
**Open questions:** none.

---
### [2026-07-06 02:00] — Danny (with Claude Code)
**What I did:** `src/algorun/refinery.py` — la **Data Refinery** del corso
(M3): la pipeline testo-libero → tokenize/lemmatize (spaCy) → entità (riuso
`nlp.dictionary_extract`) → **relazioni candidate** (NUOVO: trigger+distanza,
Rule 3) → SHACL → RDF, con benchmark P/R/F1 (overall + per tier + per
relazione) sul dataset sintetico.

**Numeri misurati su `test.jsonl` (held-out):** P=1.00 R=0.14 F1=0.24
complessivo. Precisione perfetta ovunque scatta (il filtro domain/range non
sbaglia mai una coppia); recall bassa per due limiti REALI, non bug:
1. `hasWorkoutType`/`hasEffortState` non hanno mai il loro trigger letterale
   vicino all'entità in questo corpus (sono relazioni implicite dal
   co-riferimento, non da un trigger) → R=0.00.
2. ~60% delle triple gold hanno un endpoint fuori dal vocabolario chiuso
   (titoli canzoni, nomi playlist, generi come stringa, nomi dei runner —
   nessuno di questi è un individuo dell'ontologia) → strutturalmente
   irrecuperabili da NER a dizionario.
`hasPhase`/`targetsEffort` invece: R=1.00 (trigger sempre presente e vicino).
Tier `long_distance`: R=0.00 (entità troppo lontane per la finestra di 10
token — il limite "fragile su frasi complesse" del corso, ora con un numero).

Bug trovato e corretto durante l'implementazione: `rdflib.URIRef` non è
`==` a una stringa Python identica (override deliberato in rdflib, anche se
`URIRef` eredita da `str`) — le triple predette vanno confrontate come
stringhe pure, non come `URIRef`, altrimenti il confronto con le triple gold
del JSONL (stringhe semplici) fallisce silenziosamente sempre.

Installato spaCy 3.7.2 (non 3.8.x: richiede Python 3.10+, noi siamo su 3.9)
+ `en_core_web_sm`. Demo: `python -m algorun.refinery --dataset data/synthetic/test.jsonl`.
69 test verdi (6 nuovi, con soglie sui numeri REALMENTE misurati, non
aspirazionali).

**TODOs for the other teammate:** se hai Python 3.10+, spacy 3.8.x andrà
benissimo (nessun vincolo di versione specifico salvo la nostra nota nel
requirements.txt).

**Open questions:** none. Prossimo naturale: M4 (validator supervisionato
DistilBERT/RoBERTa da confrontare contro questo baseline, sullo split train
del dataset).

---
### [2026-07-06 00:30] — Danny (with Claude Code)
**What I did:** `src/algorun/fusion.py` — il livello di **fusione** prompt +
sensore che mancava. Tre regole in ordine: (1) sicurezza vince sempre (HR ≥
93% HRmax → target calmo), (2) prompt quantitativo → BPM chirurgico MA
ri-validato dal gate SHACL con lo stato del corpo nello stesso grafo (chiuso
il buco: prima "12 km/h" scavalcava la sicurezza), (3) prompt qualitativo →
decide il sensore. Demo: `python -m algorun.fusion` (3 scenari). 63 test
verdi (4 fusion + 4 casi limite del routing). Decisioni di sessione: niente
training per ora (prima il baseline M3), niente benchmark formale qual/quant
(solo unit test).
**Open questions:** none. Prossimo passo concordato in scaletta: M3 Data
Refinery (il pezzo valutato dall'esame).

---
### [2026-07-05 19:00] — Danny (with Claude Code)
**What I did:**
- **Commenti in italiano** in `nlp.py` e `pipeline.py` (codice identico) —
  regola aggiornata in GUIDELINES: identificatori/dati/report in inglese,
  commenti in italiano.
- **GLiNER installato e benchmarkato** sul gold set: dictionary **F1 0.947**
  vs GLiNER-small **0.20** — sul nostro vocabolario chiuso vince la baseline;
  GLiNER serve per il fraseggio fuori-vocabolario (da ritestare con
  gliner_medium su Colab + gold set OOV). Aggiunto grounding "label contenuta
  nello span".
- **`sensors/gps.py`** — matematica GPS pronta per il tuo Location.csv:
  colonna `speed` preferita, fallback Haversine, filtro accuratezza ≤20 m,
  media mobile, km/h → passo, velocità → cadenza → BPM (stessa regressione di
  nlp.py). 6 test con fixture a velocità nota. Quando carichi i dati veri,
  si aggancia senza modifiche.
- **Decisione GLiREL: NO.** Le nostre relazioni sono determinate dallo schema
  → candidati pairwise vincolati da domain/range + trigger (l'opzione
  "pairwise" del Block 14). Benchmark relazioni: P/R/F1 a livello di triple
  per tier su data/synthetic/test.jsonl (arriva con M3).
**TODOs for the other teammate:** quando hai i dati GPS veri mettili in
`data/sensor/` e prova `gps_window_summary`; aggiungi al GOLD di test_nlp
frasi "fuori vocabolario" (es. "voglio spingere") per il retest GLiNER.
**Open questions:** none.

---
### [2026-07-05 17:30] — Danny (with Claude Code)
**What I did:** Built the **NLP perception** module `src/algorun/nlp.py` —
user prompt → entities → RDF triples for the ontology.
- Two backends, one interface: `dictionary` baseline (rule-based, from the
  ontology labels — always on) and `gliner` zero-shot (lazy import; run
  `pip install gliner`, ideally on Colab — not installed here, Py3.9 + torch).
- Regex pulls numbers/units (duration, speed); one `if` routes qual vs quant.
- **Quantitative = surgical BPM**: declared speed → cadence (134 + 2.9·kmh,
  clamp 150–190) → BPM target 1:1 or half-time (Van Dyck 2015). E.g. 12 km/h →
  168.8 bpm, written to the graph. Qualitative → no BPM, defers to the HR
  bridge.
- Benchmark: `evaluate()` gives P/R/F1 over a gold set of prompts; the
  dictionary baseline scores **F1 0.95** (the score GLiNER must beat).
- CLI: `python -m algorun.nlp "your prompt"`. 52 tests green (8 new).
**TODOs for the other teammate:** grow the GOLD prompt set in `tests/test_nlp.py`
with your own phrasings; install GLiNER on Colab when we do the M4 comparison.
**Open questions:** none.

---
### [2026-07-05 16:00] — Danny (with Claude Code)
**What I did:** Built the **bridge** `src/algorun/pipeline.py` — the first
end-to-end slice. It takes your BPM window (`analyze_bpm_window`), turns the
effort state into RDF, validates it with SHACL, and reads the acoustic target
back out of the ontology via SPARQL, plus the 93%-HRmax safety override.
`python -m algorun.pipeline` prints HR → effort → SHACL → target. 44 tests
green (4 new, incl. HermiT consistency on the generated graph). Nothing of
yours was modified.
**Note:** your data has no cadence, so the cadence-step rule can't fire yet —
it will once the accelerometer feature lands.
**Open questions:** none.

---
### [2026-07-05 15:00] — Danny (with Claude Code)
**What I did:** Rebuilt the ontology (v0.4) **aligned to your sensor code**:
replaced the 5 HR zones with your 4 `EffortState`s (LowEffort/TargetEffort/
HighEffort/VeryHighEffort, HRR thresholds 0.40/0.70/0.85), added `TrendState`
(Increasing/Stable/Decreasing), and used your workout goals (easy/moderate/
interval) and phases (warmup/steady/hard/recovery). Chain is now
phase → targetsEffort → effort → prescribesTarget → target. All the BPM/paper
theory lives in the ontology comments (no separate docs). Compact SHACL (one
shape per relation) + the 3 safety rules. Regenerated the synthetic dataset
to the new relations. 40 tests green. Speed/GPS left out (decided: not now).
**Open questions:** none.

---
### [2026-07-05 14:00] — Danny (with Claude Code)
**What I did:** Removed the 5 overlapping theory docs in `report/` (keep the
repo minimal — the pipeline doesn't need them; final ACSAI report comes with
M6). Restored `data/simulated/` and `data/processed/` folders. Tridentt's
sensor scripts are on main in `src/algorun/sensors/`.
**Open questions:** none.

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
