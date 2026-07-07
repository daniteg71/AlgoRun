# AlgoRun 🏃🎵

> **Struttura attuale e cosa studiare → [`STUDY_MAP.md`](STUDY_MAP.md).**
> Flusso completo (grafico + matematica) → [`docs/PIPELINE.md`](docs/PIPELINE.md).
> Alcune sezioni qui sotto descrivono un design precedente: la fonte aggiornata
> sono STUDY_MAP + PIPELINE.

**Text-driven, ontology-governed running-music recommender** — AI-LAB 2025/2026
exam project.

You tell AlgoRun what you want in one short sentence — *"tomorrow's intervals,
give me something hard"* or *"easy chill run, I've got a cold"* — and it picks
the right track and plays it on Spotify. No wearables, no live sensor stream:
the intelligence is a benchmarked NLP + Knowledge-Graph pipeline, not hardware.

> **Read `ARCHITECTURE.md` first** — the canonical design (what AlgoRun is and
> how we build it). Every decision there is tagged `[NOW]` (build now, graded or
> demoable), `[STAR]` (north-star / future), `[BENCH]` (benchmark-only) or
> `[EXT]` (hard external constraint).

## Two layers

```
OFFLINE (graded)   synthetic tiered corpus ──► Data Refinery ──► RDF Knowledge Graph
                   (tokenize→NER→candidate relations→validator→SHACL→triples)
                   BENCHMARK: rule baseline vs compact Transformers, per tier
                                            │  the KG the product queries
                                            ▼
LIVE (light)   user phrase ─► NLP dispatcher ─► ontology target + dynamic weights
               ─► Dynamic Vector Scoring over the catalog (SPARQL over the KG)
               ─► Spotify playback     (Sliding-Window memory keeps it coherent)
```

The graded backbone (ontology gate → refinery → KG → SPARQL) is the exam
deliverable; the live recommender is the product on top of it. Principle:
**ship light, benchmark heavy** — the product ships the smallest model that
works, while state-of-the-art models are run only in the offline benchmark to
show how close the light model gets.

## The recommendation system

- **NLP dispatcher** — a short utterance → a **regime** (`quantitative |
  qualitative`) + slots (speed, duration, mood, genre). Shipped model: dictionary
  + regex; SOTA models (Joint intent+slot / SetFit / GLiNER2) are benchmark
  contenders.
- **Ontology → target + dynamic weights** — the regime decides *how* the
  ontology derives the target and *which* features dominate:
  - **Quantitative:** declared pace → biomechanical cadence→BPM target
    (Van Dyck 2015/2018), narrow ±3% band, half/double-time matching; **BPM
    weight dominant**.
  - **Qualitative:** mood/effort → wide BPM band, **energy/valence dominant**;
    a health flag caps the effort.
- **Dynamic Vector Scoring** — rank catalog tracks by **weighted cosine /
  distance** to the target over `bpm/energy/valence/danceability` (normalized,
  per-feature weights from the regime), plus a **genre term** (semantic distance
  on the genre taxonomy) for personalization.
- **Sliding-Window memory** — a fixed deque of recent tracks avoids repetition
  and abrupt BPM/energy jumps between song *t−1* and *t*.

The ontology's only **runtime** job is the genre semantic distance — a BFS on a
compiled graph, no reasoner in the loop. Everything else the ontology does
(constraint gate, KG construction, SPARQL) runs **offline**.

## What is DONE and measured (honest, held-out test set)

| Piece | Where | Result |
|---|---|---|
| OWL ontology, 3 disjoint cores, effort states, acoustic targets | `ontology/algorun.owl` | consistent (HermiT); 10 competency questions pass as SPARQL tests |
| SHACL constraint gate (domain/range) | `ontology/shapes.ttl` | rejects bad domain/range before any triple enters the KG |
| **Genre taxonomy from the real dataset** | `ontology/genres.ttl`, `genre_graph.py` | 113 genres → families → super-families (146 concepts); genre→effort affinity read from the data |
| Synthetic tiered dataset, 70/15/15, 4 tiers | `data/synthetic/`, `datagen/` | 800 records, tier-balanced |
| Prompt NLP: entities + quantities, qual/quant routing | `src/algorun/exam/nlp.py` | NER F1 **0.947** (dictionary) on the prompt gold set |
| **M3 baseline** relation extraction (trigger+distance) | `src/algorun/exam/refinery.py` | graph F1 **0.241** (P 1.00, R 0.137) |
| **M4 validator** pairwise generator + DistilBERT gate | `benchmarks/validator.py` | graph F1 **0.478** (P 0.90, R 0.33) |
| Lightweight logistic validator (no GPU) | `src/algorun/exam/light_validator.py` | graph F1 **0.43** — nearly DistilBERT at a thousandth of the cost |

Multi-architecture comparison on the held-out test set (the Rule-4 benchmark):

| architecture | overall F1 | cost | size |
|---|---|---|---|
| baseline (trigger+distance rules) | 0.24 | free | 0 |
| **light validator (logistic regression)** | **0.43** | **<1 s CPU** | **~KB** |
| DistilBERT | 0.48 | ~2 min GPU/MPS | 66M params |

Key report point: the **light model reaches F1 0.43** — nearly the DistilBERT
0.48 — at a fraction of the cost. It is exactly what we ship live.

**66 tests green** (`python -m pytest`).

## Data

- `data/music/songs.csv` (git-ignored) — the catalog: 89,503 tracks with
  `bpm/energy/valence/danceability`, `genre` (113), `spotify_url`, and columns
  already aligned to the ontology (`matches_effort`, `supports_goal`,
  `supports_mood`). The KG is populated from it by direct structured mapping.
- `data/synthetic/` — the tiered JSONL dataset (course deliverable, in git).
- **Spotify reality [EXT]:** live `audio-features` is deprecated (403 since
  2024-11-27), so track features come from a static dataset; Spotify is used
  live only to list the playlist and (Premium) to start playback.

## Demos

```bash
python -m algorun.genre_graph                    # semantic distance between genres
python -m algorun.exam.nlp "tempo run at 12 km/h"     # prompt → entities → surgical BPM
python -m algorun.exam.refinery --dataset data/synthetic/test.jsonl   # M3 graph P/R/F1
python -m algorun.exam.light_validator                # baseline vs logistic (CPU, no GPU)
python -m benchmarks.validator eval                 # baseline vs trained Transformer(s)
python ontology/build_genre_taxonomy.py          # regenerate ontology/genres.ttl
```

## Repository layout

| Path | Purpose |
|---|---|
| `ARCHITECTURE.md` | **Canonical design** — read first |
| `GUIDELINES.md` | Binding course rules |
| `CLAUDE.md` | AI session protocol (pull-first, handoff-first, PR-always) |
| `ALGORITHMS.md` | Provenance ledger: every algorithm, variant, source, result |
| `collab/HANDOFF.md` | Two-person / two-AI coordination log |
| `ontology/algorun.owl` | OWL ontology (classes, relations, effort→target chain) |
| `ontology/shapes.ttl` | SHACL constraint gate |
| `ontology/genres.ttl` | Genre taxonomy (generated from the dataset) |
| `ontology/build_genre_taxonomy.py` | Generator for the genre taxonomy |
| `src/algorun/genre_graph.py` | Genre semantic distance (runtime, no reasoner) |
| `src/algorun/exam/nlp.py` | Prompt → entities/quantities → regime + slots |
| `src/algorun/exam/refinery.py` | Data Refinery: relation extraction + graph P/R/F1 |
| `benchmarks/validator.py` | Transformer validator (multi-arch benchmark) |
| `src/algorun/exam/light_validator.py` | Lightweight logistic validator (shipped) |
| `src/algorun/exam/shacl_gate.py` | SHACL gate + ontology target lookup |
| `data/synthetic/` | Tiered JSONL dataset (in git) |
| `tests/` | 66 pytest tests |

## Roadmap

- [x] **M1** — OWL ontology + SHACL shapes
- [x] **M2** — Synthetic tiered dataset (JSONL, 70/15/15, 4 tiers)
- [x] **M3** — Baseline refinery (spaCy trigger+distance → SHACL → RDF) + graph P/R/F1
- [x] **M4** — DistilBERT validator + lightweight logistic + multi-arch benchmark
- [x] **Genre taxonomy** — 113 real genres → semantic-distance graph
- [ ] **M5** — `recommender.py`: Dynamic Vector Scoring (weighted cosine + regime
  weights + genre term + Sliding Window), KG builder from `songs.csv`, NLP
  dispatcher, Spotify playlist read + playback
- [ ] **M6** — Benchmark report: five axes + reliability (calibration, ablation,
  end-to-end Precision@k) — ACSAI template
- [ ] **[STAR]** — optional live GPS/HR sensors + real-time loop (designed for in
  `ARCHITECTURE.md`, not a deliverable requirement)

## Setup

```bash
python3 -m venv .venv          # Python 3.9 works (Apple Silicon incl. MPS)
source .venv/bin/activate
pip install -r requirements.txt   # on Python 3.9 pin spacy<3.8 (see note inside)
python -m spacy download en_core_web_sm
python -m pytest                  # 66 green
```

## Team

Two students, each pair-programming with their own AI assistant. Coordination
happens through `collab/HANDOFF.md` — read it first, always.
