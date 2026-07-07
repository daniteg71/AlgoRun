# ARCHITECTURE.md — AlgoRun Architectural Design Document

> **Status: canonical design (north-star + build-now).** This is the single
> source of truth for *what AlgoRun is* and *how we build it*. Any teammate or
> AI assistant starting work reads this together with `GUIDELINES.md` (binding
> course rules), `CLAUDE.md` (session protocol) and `README.md` (milestones).
>
> It supersedes the old "real-time DJ with continuous sensors" framing. The
> vision is preserved as a north-star; what we *build and grade now* is the
> lightweight, text-driven core. Every claim below is tagged so nobody builds
> the wrong thing:
>
> | Tag | Meaning |
> |---|---|
> | **[NOW]** | Build now. It is graded and/or demoable, and it works on a laptop. |
> | **[STAR]** | North-star / future extension. Designed for, not required. Do not block the deliverable on it. |
> | **[BENCH]** | Exists only inside the offline benchmark (the report), never shipped in the live product. |
> | **[EXT]** | Hard external constraint we verified (dead API, Premium, etc.) — not negotiable. |

---

## 0. Current design — TWO separate tracks (read this first)

AlgoRun is **two tracks that share only the genre taxonomy**. Keeping them
separate is what keeps the code simple. Do not mix them.

### Track A — THE PRODUCT (the running DJ) = the recommendation system
Input: a runner's phrase **+ live sensor data**. Output: the next song.

```
[START]  frase → intent.py (SetFit + regex) → {type, numbers, params}   (target iniziale)
[DURANTE] sensori → sensor.py → shot (HRR/effort/trend)
                    controller.py  = IL "MEZZO": per ogni canzone aggrega gli shot,
                                     aggiorna il target (per tipo) + safety (HRR≥0.90)
                    scorer.py  →  score → probabilità (softmax) → prossima canzone
```

Files: `intent.py`, `sensor.py`, `scorer.py`, `controller.py`, `genres.ttl`.
The only ontology it uses is **`genres.ttl`** (genre distance, Rada 1989).
**No SHACL, no refinery, no `algorun.owl`.** Sensors are **[NOW]** here (they are
the master: the data already exists in `data/processed/physiological_windows.csv`).

### Track B — THE EXAM (Block 14 deliverable) = text → Knowledge Graph
Synthetic text → ontology-governed RDF, benchmarked across architectures.
Files: `algorun.owl`, `datagen/`, `refinery.py`, `shacl_gate.py`,
`light_validator.py`, `benchmarks/`. **The recommender uses NONE of these.**

### The recurring questions, answered for good
- **What is `light_validator` for?** Track B only. It's the lightweight logistic
  validator that decides VALID/INVALID on candidate KG triples in the refinery,
  and it's the benchmark champion (F1 0.43 ≈ DistilBERT). Nothing to do with songs.
- **Why is the ontology still "general" and not just genres?** Because
  `algorun.owl` is **Track B's** (the exam). The product/recommender touches
  **only `genres.ttl`**. They are two different files, two different jobs.
- **How is the "middle" (user input + sensors during the run) handled, and by
  which code?** The phrase sets the **initial** target once (`intent.py`); the
  sensors **continuously adjust** it. They meet in **`controller.py`**, which every
  song aggregates the shots, calls `adapt()` (per-type + safety), then asks
  `scorer.py` for the next song. `controller.py` IS the middle.

### What the colleague still needs to build the recommender well (Track A gaps)
1. **mood→genre seed** — the genre term in `scorer.py` stays off until a seed
   genre is passed; wire mood (from the phrase) → seed genre.
2. **interval square-wave** — `controller.adapt()` currently "holds" for interval;
   add the A/B target on a timer.
3. **Spotify playback** — `controller` picks the song but does not play it yet.
4. **real timing** — how many shots per song (derive from the track duration).
5. **tuning** of bands/weights/τ (ablation for the paper).

The score→probability engine he builds on: **`scorer.rank(target)`** → every song
with `score` + `prob`; **`scorer.choose(target)`** samples one. `make_target()`
builds the target from the NLP params + the sensor-updated bpm/energy.

---

## 1. Objective and the task

AlgoRun turns a runner's **free-text request** into the **ideal track**, chosen
by an **ontology-governed, benchmarked** pipeline, and plays it on Spotify.

The task, stripped to its essence, is the course mandate applied to running
music: **unstructured text → structured RDF, governed by a custom ontology,
benchmarked across ML architectures**, plus a light product layer that queries
the resulting Knowledge Graph and acts on it.

Two user regimes, one system:

- **Quantitative regime** — directive, measurable requests: *"2 ore a 12 km/h"*,
  *"fartlek"*, *"intervals at 180 spm"*.
- **Qualitative regime** — mood / perceived-effort requests: *"oggi sono
  stanco"*, *"corsa chill"*, *"ho il raffreddore"*.

The regime is not cosmetic: it changes **how the ontology derives the target**
and **which musical features dominate the scoring**. That branching is the
theoretical heart of the project.

## 2. Design principles (course rigor + state of the art)

1. **Deterministic boundaries around probabilistic models.** Probabilistic
   models *propose*; the symbolic layer (ontology domain/range + SHACL)
   *disposes*. Safety and validity decisions never live inside a learned model.
2. **Ship light, benchmark heavy.** The live product ships the smallest model
   that does the job. State-of-the-art models are run **[BENCH]** to establish
   the performance *ceiling*, so the report can show how close the light model
   gets at a fraction of the cost. This is the strongest result we can tell —
   and it is exactly the "compare a rule baseline vs. compact Transformers"
   the course asks for.
3. **The ontology restricts and derives; it never generates.** It is a
   constraint gate and a source of target parameters, not a text generator.
4. **The comparison is the deliverable.** We never pick a model by faith and
   defend it. We define a motivated candidate set, benchmark it fairly on an
   untouched test split (per tier), and let the numbers pick the winner. The
   surprising honest result (a light model nearly matching a heavy one) is
   itself the headline of the report.

## 3. Architecture overview

```
                          ┌──────────────────── OFFLINE (graded) ────────────────────┐
                          │  synthetic tiered corpus ──► Data Refinery ──► RDF KG      │
                          │  (tokenize→NER→candidate relations→validator→SHACL→triples)│
                          │  BENCHMARK: rule baseline vs compact Transformers, per tier│
                          └───────────────────────────────┬───────────────────────────┘
                                                           │ the KG the product queries
                                                           ▼
 user phrase ──►  (1) NLP DISPATCHER ──►  (2) ONTOLOGY REASONING ──►  (3) DYNAMIC VECTOR ──►  (5) ACT
   ≤20 words        intent + slots           target vector + dynamic       SCORING              Spotify
                    {quant | qual}           feature weights (the branch)   (weighted distance   playback
                         │                        │  SHACL gate              to target, SPARQL    + Safety
                         │                        │                          over the KG)         Override
                         └────────────────────────┴──► (4) SLIDING WINDOW MEMORY (recent tracks, phase) ──┘
```

Stages:

1. **NLP Dispatcher [NOW baseline / BENCH SOTA]** — parse a short utterance into
   a sentence **intent** (`quantitative | qualitative | invalid`) and **slots**
   (speed, duration, mood, workout type, genre…).
2. **Ontology reasoning [NOW]** — the activated concepts produce a **target
   vector** (BPM / energy / valence bands) *and* a **dynamic weight profile**.
   SHACL gates the produced target.
3. **Dynamic Vector Scoring [NOW]** — rank catalog tracks by **weighted
   distance / weighted cosine** to the target; weights come from the regime.
4. **Sliding Window Memory [NOW]** — keep a short history of recently played
   tracks to preserve workout-phase coherence and avoid repetition / jarring
   stylistic jumps.
5. **Act [NOW]** — start playback of the winning track on Spotify; a
   physiological **Safety Override** can pre-empt the request.

## 4. The two regimes — the theory that makes it non-arbitrary

The ontology emits, per regime, a **target** and a **weight profile**
`w = (w_bpm, w_energy, w_valence, w_genre)`.

### Quantitative branch [NOW]
The declared pace/speed drives a **biomechanical entrainment** target:

- `cadence(spm) ≈ 150 + 3.0 · speed(km/h)`, clamped to `[150, 190]`
  (reconciled with the existing `nlp.py` regression; tunable, and overridden by
  a real cadence signal when present — **[STAR]**).
- `target_bpm = cadence`. A track matches at **1:1, ½×, or 2×** the target
  within a **±3% band** (≈ ±5 BPM near 180). Half/double-time keeps slow-but-
  groovy tracks instead of discarding them — the single correctness point most
  tools get wrong.
- Weights: **BPM dominant** (e.g. `w_bpm ≈ 0.8`), energy medium, valence low.
- Theory / citations: Van Dyck et al. **2015** (*Sports Medicine–Open*) and
  **2018** (*PLOS ONE*): spontaneous cadence↔tempo entrainment holds within
  ~±2.5–3%; a slight tempo-ahead bias raises motivation.

### Qualitative branch [NOW]
No measurable target → **interpret effort** and optimize **arousal**:

- Mood / effort words → `EffortState` (chill … push); health flags
  (*"raffreddore"*) cap the effort to a recovery target.
- Target: **wide** BPM band + a **specific energy band** (chill → low energy,
  push → high energy); valence follows mood.
- Weights: **energy / valence (affective features) dominant**, BPM tolerance
  wide.

### Genre–User crossing [NOW] (both regimes)
The final score includes a genre bonus/penalty = intersection of
(a) the genre's *functional* suitability for the effort type (training-music
theory) and (b) the user's *historical* genre preferences (from their catalog).
Personalized, but athletically valid.

### Safety Override [NOW logic / STAR trigger]
A physiological ceiling that **invalidates the initial intent**: if heart rate
crosses a tolerance threshold, an aggressive quantitative intent ("push max") is
forced into a recovery state. The *logic and the SHACL rule* are built now and
tested on simulated/declared effort; the *live HR trigger* activates only when a
real HR stream is present (**[STAR]**). Crucially this is a **deterministic,
physiological** override enforced by SHACL — never a probabilistic model's call.

## 5. NLP Dispatcher — candidates and benchmark

The dispatcher is where "course pipeline vs. state of the art" is made concrete.

- **Shipped model [NOW]:** rule-based **dictionary (from OWL labels,
  longest-match) + regex** for the quant/qual signal (a number+unit is a nearly
  deterministic quantitative marker). It is instant, fully explainable, and — on
  a **closed** ontology vocabulary — a genuinely strong baseline (measured
  dictionary NER F1 **0.947** on the prompt gold set).
- **SOTA contenders [BENCH]** establishing the ceiling:
  - **Joint Intent Classification + Slot Filling** (a ~150-line 2-head
    DistilBERT written on modern `transformers`, method per Chen et al. 2019,
    reference impl `monologg/JointBERT`). One forward pass → intent + BIO slots.
  - **GLiNER / GLiNER2** — schema-driven label-guided extraction (+ built-in
    classification and a numeric slot in GLiNER2).
  - **SetFit** — few-shot intent classification, trains in seconds on CPU.
  - **A small instruction-tuned LLM with structured (JSON) output** as the
    modern upper bound for robustness on paraphrastic input.
- **Honest expectation & evaluation protocol:** on a small closed vocabulary the
  rule baseline often *matches or beats* the Transformers, which mainly win on
  open-vocabulary / paraphrastic slots. Therefore we evaluate on **hand-written**
  phrases (never a slice of the synthetic generator), report intent accuracy +
  slot-F1 (`seqeval`) + **sentence exact-match**, and include the rare `invalid`
  class explicitly. If a heavy model only wins on synthetic-held-out but ties the
  baseline on real phrasing, we do not ship it — and we say so in the report.

## 6. Dynamic Vector Scoring — approach and benchmark

- **Approach [NOW]:** rank catalog tracks by **weighted distance to the
  ontology-derived target** over normalized features (tempo/energy/valence,
  optionally danceability). Two non-negotiable prep steps: **(a) normalize** each
  feature to a common scale (so tempo does not dominate energy) and **(b) apply
  `sqrt(weight)` per feature** so weights act linearly inside the squared
  distance. Weighted **cosine** is the alternative when we want proportion, not
  magnitude; weighted **Euclidean** is the default for a concrete target point.
- **Why not a heavier recommender:** for a *tabular* BPM/energy/valence target,
  transparent weighted distance is near-optimal and fully explainable; a learned
  ranker needs labels we do not have. Learned audio-feature **embeddings**
  (contrastive) are recorded as a **[STAR/BENCH]** option, not the default.
- **[BENCH] axis:** rule thresholds vs. weighted distance vs. a small supervised
  classifier for the Song→band mapping (see §9).

## 7. Data and Spotify integration [EXT]

Verified constraints (2026) shape the data path:

- **Live audio-features are dead.** Spotify deprecated `audio-features` /
  `audio-analysis` on 2024-11-27 → **403** for new apps. BPM/energy/valence come
  from an **offline Kaggle dataset** (`maharshipandya/spotify-tracks-dataset`,
  ~114k tracks, CC0), joined to the user's tracks by **fuzzy title+artist**
  (`rapidfuzz`; realistic coverage ~60–85%; unmatched tracks are flagged
  *unclassified*, never silently dropped).
- **Playlist listing is live and unrestricted** (`playlist_items`).
- **Playback is live but Premium-gated.** `spotipy.start_playback` requires
  **Spotify Premium** + an **active device**. A **no-Premium fallback** [NOW]
  shows/opens the chosen track instead of auto-playing, so the demo never dies.
- **Auth:** OAuth Authorization Code (Development Mode, 25-user cap, redirect
  `http://127.0.0.1:8888/callback`).

Every real track is classified into a target band and written to the KG as RDF
(direct structured mapping); the recommender then reads **only from the KG via
SPARQL** — the KG is the single source of truth.

## 8. Knowledge Graph and the course pipeline (the graded backbone) [NOW]

This is the part the exam grades, and it is the robust core:

- **Ontology** — trimmed OWL (`ontology/algorun.owl`): Runner, WorkoutSession,
  WorkoutType, TrainingPhase, EffortState (now *text-derived*), Song, Genre,
  Playlist, AcousticTarget (BPM/energy/valence bands), directional relations
  with explicit domain/range + inverses. The live-sensor, HR/cadence data
  properties and the physiological safety props are retained as an **[STAR]**
  layer, disabled by default.
- **Synthetic tiered dataset** — LLM-authored **constrained by the ontology**,
  JSONL with gold entities+triples, **70/15/15**, four complexity tiers
  (explicit / implicit / long-distance / nested). Re-themed to editorial track
  descriptions ("*a 174 BPM techno anthem, ideal for interval sprints*").
- **Data Refinery** — fixed order: tokenize → lemmatize → entity/mention
  detection (→ IRIs) → candidate relation extraction → **validator** → SHACL
  grounding → RDF KG. Generator/validator dissociation preserved.
- **Recommender** — reads the KG via **SPARQL**, applies the dynamic vector
  scoring in Python, returns the ranked tracks.

## 9. Benchmarking plan — five axes (the report)

| # | Axis | Candidates | Metric |
|---|---|---|---|
| 1 | Relation extraction (build KG from text) | spaCy baseline vs DistilBERT vs RoBERTa vs light-logistic | graph P/R/F1, per tier |
| 2 | Entity detection (NER) | dictionary vs GLiNER vs GLiNER2 | span F1, per tier |
| 3 | Intent + slot (dispatcher) | dict+regex vs JointBERT vs SetFit vs DistilBERT×2 vs small-LLM | intent acc + slot-F1 + exact-match, on hand-written phrases |
| 4 | Song → target band | rule thresholds vs supervised classifier | accuracy + confusion matrix |
| 5 | Cost / efficiency | all of the above | latency, params, memory |

**Reliability (the "how safe is the whole thing" ML capstone):**
- Song→band classifier as a real supervised model: train/test, confusion
  matrix, **calibration (ECE / reliability diagram)**.
- **End-to-end headline metric:** given a phrase with a known intended target,
  do the recommended track's *real* audio features fall in the correct band?
  **Precision@k**.
- **Ablation:** disable SHACL / disable the validator / swap the extractor →
  measure the end-to-end F1 drop, quantifying each component's contribution.

## 10. What we build NOW vs north-star vs benchmark-only

| Concern | Decision |
|---|---|
| Text-driven request → recommendation → playback | **[NOW]** |
| Ontology + synthetic dataset + Data Refinery + SPARQL recommender | **[NOW]** |
| Dynamic Vector Scoring + dynamic weights + genre-user crossing | **[NOW]** |
| Sliding Window Memory | **[NOW]** |
| Shipped NLP = dictionary + regex | **[NOW]** |
| SHACL safety rule + override *logic* (on declared/simulated effort) | **[NOW]** |
| Continuous GPS + HR sensor streams; live HR safety trigger; real-time never-interrupt loop | **[STAR]** — architecture ready, not required for the deliverable |
| JointBERT / RoBERTa / GLiNER(2) / small-LLM | **[BENCH]** — ceiling in the report, not shipped |
| Audio features from Kaggle join; Premium-gated playback | **[EXT]** — non-negotiable external reality |

## 11. Honest risks

- **Fuzzy-join coverage** (~60–85%): some real tracks stay *unclassified* —
  stated, not hidden.
- **Premium requirement** for playback: keep at least one Premium account for
  the demo; the no-Premium fallback covers the rest.
- **Synthetic overfitting** of any heavy dispatcher: mitigated by hand-written
  eval and diverse templates; may simply confirm the rule baseline wins.
- **Real-time / sensors** are the heavy, ungraded, hard-to-finish part — kept
  as a north-star on purpose, so it never blocks the graded deliverable.

## 12. Deliverables → course rules

| Course deliverable (GUIDELINES R5) | Where |
|---|---|
| Custom domain ontology (OWL/SKOS, strict domain/range) | `ontology/algorun.owl`, `shapes.ttl` |
| Synthetic annotated tiered dataset | `data/synthetic/*.jsonl` |
| Working software pipeline | Refinery (build KG) + recommender (query KG) + Spotify layer |
| Benchmarking report | five axes above + reliability capstone (ACSAI template) |

---

*This document defines direction, not code. Implementation follows the course
pipeline order and the principle "ship light, benchmark heavy," and is planned
milestone by milestone in `README.md`.*
