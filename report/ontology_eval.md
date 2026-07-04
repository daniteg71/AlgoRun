# AlgoRun Ontology — Evaluation Report (v0.2)

Ontology evaluation is a course deliverable (Block 13). We evaluate on three
levels: functional (competency questions), logical (reasoner), and quality
(pitfalls / taxonomy).

## 1. Functional — competency questions

The 10 competency questions from `ontology_design.md` are encoded as SPARQL
queries in `tests/test_competency_questions.py` and run against a small valid
sample KG (`src/algorun/ontology/evaluation.py::sample_kg`). All 10 pass:
the ontology can answer every question it was designed for.

| CQ | Question | Status |
|----|----------|--------|
| CQ1 | Songs suiting the sprint phase in Z5 | ✅ |
| CQ2 | Song BPM matching cadence ~172 | ✅ |
| CQ3 | Playlist built for a session | ✅ |
| CQ4 | Zone of the heart rate in a session | ✅ |
| CQ5 | Preferred genres of the runner | ✅ |
| CQ6 | Sessions and their workout type | ✅ |
| CQ7 | Songs matching a zone AND a preferred genre | ✅ |
| CQ8 | Phase sequence and per-phase target zone | ✅ |
| CQ9 | Readings recorded in a session | ✅ |
| CQ10 | BPM curve across the session's phases | ✅ |

## 2. Logical — reasoner consistency

Checked with HermiT via `owlready2` (`check_consistency`, requires Java).

- Ontology alone: **consistent**.
- Ontology + valid sample ABox: **consistent**.
- Ontology + an individual typed as both `Runner` (⊑ Agent) and
  `WorkoutSession` (⊑ Process): **inconsistent** — the three-core
  disjointness axioms bite, as intended.

This is the logical counterpart of the SHACL gate: the reasoner proves the
schema is coherent; SHACL (closed-world, inference off) rejects individual
bad triples at ingestion.

## 3. Quality — pitfalls and taxonomy

- **OOPS! (OntOlogy Pitfall Scanner)** — to run before the final report by
  uploading `ontology/algorun.owl` to https://oops.linkeddata.es/. Expected
  clean because v0.2 fixed the common pitfalls proactively: P04 (unconnected
  classes — every class hangs under a core), P11 (missing domain/range — all
  present), P13 (missing inverses — all inverses declared), P19 (multiple
  domains — none). Results to be pasted here.
- **OntoClean** (Guarino & Welty) — informal taxonomy check: our cores are
  rigid sortals (Agent, Process, InformationEntity carry identity and are
  mutually disjoint), subclasses inherit identity cleanly, and no anti-rigid
  class subsumes a rigid one. No OntoClean violations found by inspection.

## Reproduce

```bash
python -m pytest tests/test_competency_questions.py tests/test_ontology_v2.py
```
