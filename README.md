# AlgoRun 🏃🎵

**Ontology-driven AI running playlist manager** — AI-LAB 2025/2026 exam project.

AlgoRun turns raw sensor data from a run (Sensor Logger: GPS, accelerometer,
barometer, heart rate) plus the user's desired workout type into the *right*
playlist — through a fully ontology-governed NLP pipeline, as mandated by the
course.

## How it works

```
Sensor Logger CSV ──► feature extraction ──► session narrative (text) ─┐
User workout intent (text) ────────────────────────────────────────────┤
LLM synthetic corpus (tiered JSONL) ───────────────────────────────────┤
                                                                       ▼
     tokenize → lemmatize → mention detection → candidate triples
     → Transformer validator (binary logic gate) → SHACL grounding
                                                                       ▼
                                       RDF Knowledge Graph (rdflib)
                                                                       ▼
    direct sensor→triples mapping ──► ground-truth graph (evaluation)  │
                                                                       ▼
                SPARQL playlist rules → ordered playlist (BPM curve)
```

The ontology (`ontology/algorun.owl`) restricts and validates everything:
no triple enters the Knowledge Graph without passing the SHACL constraint
gate. The playlist recommender reads exclusively from the KG via SPARQL.

## Repository layout

| Path | Purpose |
|---|---|
| `CLAUDE.md` | AI session protocol (pull-first, handoff-first, PR-always) |
| `GUIDELINES.md` | Binding course rules — read before coding |
| `ALGORITHMS.md` | Provenance ledger: algorithms, variants, sources, papers |
| `collab/HANDOFF.md` | Two-person/two-AI coordination log |
| `ontology/` | OWL ontology + SHACL shapes (theory in the comments) |
| `data/synthetic/` | Tiered JSONL dataset (70/15/15) |
| `src/algorun/ontology/` | Ontology loader + evaluation (reasoner, competency questions) |
| `src/algorun/datagen/` | Synthetic NLP-dataset generator |
| `src/algorun/sensors/` | Sensor pipeline (BPM → effort state; simulator; window builder) |
| `tests/` | pytest suites |

Folders for data that isn't in git yet are created on demand: real Sensor
Logger exports (`data/sensor/`), the music catalog (`data/music/`), and the
regenerable sensor outputs (`data/simulated/`, `data/processed/`) — all
git-ignored.

## Milestones

- [x] **M0** — Scaffolding (protocol files, repo tree)
- [x] **M1** — OWL ontology + SHACL shapes + label dictionary
- [x] **M2** — Synthetic tiered dataset (JSONL, 70/15/15)
- [ ] **M3** — Baseline pipeline (spaCy rule-based → SHACL → RDF) + first P/R/F1
- [ ] **M4** — Advanced pipeline (GLiNER, GLiREL, DistilBERT/RoBERTa validators)
- [ ] **M5** — Sensors + music catalog + SPARQL recommender + demo CLI
- [ ] **M6** — Benchmark report (per-tier, per-architecture P/R/F1)

## Setup

```bash
python3 -m venv .venv          # Python ≥ 3.9 (3.11+ recommended for M4 training)
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

Run the tests with `python -m pytest`.

## Team

Two students, each pair-programming with their own AI assistant. Coordination
happens through `collab/HANDOFF.md` — read it first, always.
