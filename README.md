# AlgoRun 🏃🎵

**Ontology-driven AI running playlist manager** — AI-LAB 2025/2026 exam project.

AlgoRun turns live sensor data (heart rate, accelerometer) plus the user's
free-text workout intent into the *right* music: an ontology decides *what*
kind of sound each physiological state needs, SHACL guards safety, and a
Transformer validator turns noisy text into reliable RDF triples.

## Architecture (the 5-step loop)

```
1. EDGE       Sensor Logger streams HR/accelerometer  ──►  local server
2. PERCEIVE   user prompt ──► NLP (dictionary/GLiNER + regex) ──► RDF A-Box
              sensor window ──► HRR ──► effort state  ──► RDF A-Box
3. REASON     SHACL constraint gate + SPARQL: effort ──► acoustic target
              (BPM/energy band), safety rules always win (93% HRmax line)
4. RETRIEVE   target point ──► nearest track in the music catalog   [todo M5]
5. ACT        Spotify API switches the song                          [todo M5]
```

## What is DONE and measured (honest numbers, held-out test set)

| Piece | Module | Result |
|---|---|---|
| OWL ontology, 3 disjoint cores, effort states, acoustic targets, safety props | `ontology/algorun.owl` | consistent (HermiT); 10 competency questions pass as SPARQL tests |
| SHACL constraint gate (domain/range + 3 SPARQL safety rules) | `ontology/shapes.ttl` | rejects bad domain/range, >5% cadence jumps, energetic targets at critical HR |
| Synthetic tiered dataset, 70/15/15 | `data/synthetic/`, `src/algorun/datagen/` | 800 records, 4 complexity tiers, balanced |
| Sensor bridge: BPM window → HRR → effort → SHACL → target | `src/algorun/pipeline.py` | demo: `python -m algorun.pipeline` |
| Prompt NLP: entities + quantities, qual/quant routing, surgical BPM from speed | `src/algorun/nlp.py` | NER F1 **0.947** (dictionary) vs 0.20 (GLiNER-small) on prompt gold set |
| Fusion prompt+sensor, safety-first precedence | `src/algorun/fusion.py` | demo: `python -m algorun.fusion` |
| GPS math (Haversine, smoothing, speed→cadence→BPM) — awaiting real data | `src/algorun/sensors/gps.py` | 6 tests on a known-speed synthetic run |
| **M3 baseline** relation extraction (trigger+distance, course Rule 3) | `src/algorun/refinery.py` | graph F1 **0.241** (P 1.00, R 0.137) |
| **M4 validator** pairwise generator + DistilBERT logic gate | `src/algorun/validator.py` | graph F1 **0.478** (P 0.90, R 0.33); long-distance tier 0.00 → 0.47 |

Multi-architecture comparison on the held-out test set (Rule 4) — from the
rule-based baseline to the heavy Transformer, showing the cost/benefit curve:

| architecture | overall F1 | cost | size |
|---|---|---|---|
| baseline (trigger+distance rules) | 0.24 | free | 0 |
| **light validator (logistic regression)** | **0.43** | **<1 s CPU** | **~KB** |
| DistilBERT | 0.48 | ~2 min GPU/MPS | 66M params |
| RoBERTa-base | *collapsed* (majority-class, lr too high — needs retuning) | GPU | 125M params |

Key takeaway (a strong report point): the **lightweight logistic-regression
validator reaches F1 0.43** — nearly the DistilBERT 0.48 — at a **thousandth of
the cost and none of the fragility**. It handles the 19/81 class imbalance with
`class_weight="balanced"`, exactly what RoBERTa failed at.

75 tests green (`python -m pytest`).

## Demos

```bash
python -m algorun.pipeline                       # sensor → effort → SHACL → target
python -m algorun.nlp "tempo run at 12 km/h"     # prompt → entities → surgical BPM
python -m algorun.fusion                         # prompt+sensor arbitration (safety first)
python -m algorun.refinery --dataset data/synthetic/test.jsonl   # M3 graph P/R/F1
python -m algorun.light_validator               # baseline vs logistic-regression (CPU, no GPU)
python -m algorun.validator train --arch distilbert              # ~2 min on Apple MPS
python -m algorun.validator eval                 # baseline vs every trained Transformer
```

## RoBERTa comparison (Rule 4: "multiple Transformer architectures")

The code is ready (`--arch roberta`), but roberta-base (125M params) is heavy
for a laptop — train it on **Google Colab** (free T4 GPU) instead:

```python
# Colab: Runtime > Change runtime type > T4 GPU, then run ONE cell (don't interrupt):
!git clone https://github.com/daniteg71/AlgoRun.git
%cd AlgoRun
# NOTE: no owlready2 here — it compiles slowly from source and is NOT needed for
# training (it's only for the HermiT reasoner). torch/transformers are usually
# preinstalled on Colab; the validator auto-uses the T4 GPU (cuda).
!pip -q install rdflib pyshacl "spacy>=3.7" transformers pandas
!python -m spacy download en_core_web_sm -q
!pip -q install -e .
!python -m algorun.validator train --arch roberta
!python -m algorun.validator eval
```

Paste the printed P/R/F1 back into `ALGORITHMS.md`.

## Repository layout

| Path | Purpose |
|---|---|
| `CLAUDE.md` | AI session protocol (pull-first, handoff-first, PR-always) |
| `GUIDELINES.md` | Binding course rules — read before coding |
| `ALGORITHMS.md` | Provenance ledger: every algorithm, variant, source, measured result |
| `collab/HANDOFF.md` | Two-person/two-AI coordination log |
| `ontology/` | OWL ontology + SHACL shapes (theory & citations in the comments) |
| `data/synthetic/` | Tiered JSONL dataset (course deliverable, in git) |
| `src/algorun/ontology/` | Ontology loader, label dictionaries, reasoner evaluation |
| `src/algorun/datagen/` | Synthetic dataset generator + validator |
| `src/algorun/sensors/` | BPM analysis (teammate), simulator, window builder, GPS math |
| `src/algorun/nlp.py` | Prompt → entities/quantities → RDF (qual/quant routing) |
| `src/algorun/pipeline.py` | Sensor bridge: effort → SHACL → acoustic target |
| `src/algorun/fusion.py` | Prompt+sensor arbitration, safety always wins |
| `src/algorun/refinery.py` | M3 Data Refinery: relation extraction + graph P/R/F1 |
| `src/algorun/validator.py` | M4: pairwise generator + Transformer validator (multi-arch) |
| `tests/` | 73 pytest tests |

`models/` (trained weights) and on-demand data folders (`data/sensor`,
`data/music`, `data/simulated`, `data/processed`) stay out of git.

## Still missing (roadmap)

- **RoBERTa numbers** — code ready, run on Colab (above).
- **M5**: music catalog + nearest-track retrieval, live Sensor Logger webhook
  server, Spotify (spotipy) playback control; hysteresis / playback-lock /
  panic-button controller (designed, not coded); real sensor & GPS recordings.
- **Integration**: refinery/validator output does not yet feed a persistent
  Knowledge Graph that fusion/recommender read from.
- **M6**: final ACSAI benchmark report; OOPS! scan of the ontology.

## Milestones

- [x] **M0** — Scaffolding (protocol files, repo tree)
- [x] **M1** — OWL ontology + SHACL shapes + label dictionary
- [x] **M2** — Synthetic tiered dataset (JSONL, 70/15/15)
- [x] **M3** — Baseline pipeline (spaCy trigger+distance → SHACL → RDF) + graph P/R/F1
- [x] **M4** — DistilBERT validator (RoBERTa: code ready, Colab pending; GLiNER benchmarked on prompts)
- [ ] **M5** — Music catalog + retrieval + live server + Spotify
- [ ] **M6** — Benchmark report (ACSAI template)

## Setup

```bash
python3 -m venv .venv          # works on Python 3.9 (Apple Silicon incl. MPS training)
source .venv/bin/activate
pip install -r requirements.txt   # on Python 3.9 use spacy<3.8 (see note inside)
python -m spacy download en_core_web_sm
python -m pytest                  # 73 green
```

## Team

Two students, each pair-programming with their own AI assistant. Coordination
happens through `collab/HANDOFF.md` — read it first, always.
