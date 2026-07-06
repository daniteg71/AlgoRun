# GUIDELINES.md — Binding Course Rules (AI-LAB 2025/2026)

> **This file is a commitment.** Any AI assistant (or human) writing code in this
> repository MUST read this file first and verify every applicable checklist
> below **before and after** producing code. These rules are distilled from the
> official course material (Block 14 — Project Description, Avola-Lezochè,
> AI-LAB 2025/2026) and are **non-negotiable**. If a proposed change conflicts
> with a rule here, the rule wins — stop and flag the conflict instead of coding
> around it.

## The Engineering Mandate

Design an end-to-end software system that transforms **unstructured text into
structured RDF triples**, governed by a **custom ontology** and **benchmarked
against multiple ML architectures**. Applied to our domain: an AI that manages
a running playlist from sensor metadata (Sensor Logger) + the user's desired
workout type.

We are not just parsing text. We are designing **deterministic boundaries
around probabilistic models** to build reliable, human-centric intelligent
systems.

## Rule 1 — The ontology restricts and validates; it never generates

- [ ] The domain ontology is a formal OWL artifact (`ontology/algorun.owl`)
      with **hierarchical classes**, **directional relations (forward/inverse)**
      and **explicit domain/range constraints**.
- [ ] No data is ever "generated from" the ontology. The ontology is a
      **constraint gate**: anything that violates a domain/range pair is
      rejected (e.g., `performs` with domain `Agent` must reject a
      `PhysicalLocation` subject).
- [ ] Every relation used anywhere in the codebase MUST exist in the ontology
      with a declared domain and range.

## Rule 2 — Synthetic dataset: tiered, annotated, 70/15/15

- [ ] Dataset is generated via LLM prompting **constrained by the ontology**
      (concepts/relations injected into the prompt; output must only use them).
- [ ] Format: **JSONL**, with gold annotations (entities + triples) per record.
- [ ] Split: **70% train / 15% validation / 15% test** — always, no exceptions.
- [ ] Every record is labeled with one of the **4 complexity tiers**:
      1. **Explicit** — direct trigger words in a single, simple sentence.
      2. **Implicit** — requires synonym resolution or broader context.
      3. **Long-Distance** — entities separated by multiple clauses/sentences.
      4. **Nested** — dense, ambiguous text with multiple overlapping triples.
- [ ] Tier distribution is tracked and reported; evaluation is broken down
      **per tier**.

## Rule 3 — The Data Refinery pipeline order is fixed

```
raw text → Tokenization → Lemmatization → Entity & Mention Detection (→ IRIs)
        → Candidate Relation Extraction → Validator (Transformer/LLM)
        → Semantic Grounding (SHACL) → RDF Knowledge Graph
```

- [ ] Stages are **modular** (separate modules, clean interfaces, testable in
      isolation) and communicate via the documented intermediate artifacts:
      `raw_text.jsonl → mentions_list → candidate_triples → validated_triples
      → grounded_triples`.
- [ ] Entity detection baseline = **rule-based dictionary matching from OWL
      labels, longest-match-first**. Advanced = **GLiNER** (label-guided NER
      with semantic roles derived from the ontology).
- [ ] Relation extraction baseline = **spaCy trigger-word + token-distance
      pairing** (and we document its known limits: brittle on nested
      sentences, trigger bias, low recall on implicit relations).
- [ ] **Generator/Validator dissociation** (the architectural shift): the
      model never guesses relations from scratch as a generator compiled to
      the ontology. Candidate generation (GLiREL / pairwise) is separate from
      the **supervised Transformer binary validator** that acts as a *stable
      logic gate* (VALID / INVALID) for proposed relations.
- [ ] **SHACL enforces truth** (`ontology/shapes.ttl`): strict domain/range
      validation runs **before** final RDF creation. No triple enters the
      Knowledge Graph without passing the SHACL gate.

## Rule 4 — Benchmarking is mandatory and graph-based

- [ ] Compare the **spaCy baseline** against **multiple Transformer
      architectures** as validators (at minimum: DistilBERT and RoBERTa-base;
      more families — XLNet, BigBird, T5 — are welcome).
- [ ] Metrics: **Precision = TP/(TP+FP)**, **Recall = TP/(TP+FN)**, **F1**,
      computed by comparing the **predicted graph vs. the actual ground-truth
      graph** (triple-level TP/FP/FN).
- [ ] Results reported **per complexity tier** and **per architecture**, with
      speed/efficiency trade-offs discussed.
- [ ] Training uses the train split, tuning uses validation, and final numbers
      are reported **only on the untouched test split**.

## Rule 5 — Deliverables

1. **Custom Domain Ontology** — OWL/SKOS file with strict domain/range logic.
2. **Synthetic Annotated Dataset** — tiered JSONL (train/val/test).
3. **Working Software Pipeline** — this GitHub repository with NLP scripts,
   verifier models, and RDF exporter.
4. **Benchmarking Report** — comprehensive analysis of the spaCy baseline vs.
   Transformer architectures (ACSAI report template).

## Project-specific commitments (AlgoRun)

- [ ] Sensor scope (team decision 2026-07-04): exactly **two sensors** —
      accelerometer (→ cadence) and heart-rate sensor (→ beats), from
      **Sensor Logger**. GPS/speed math is ready in `sensors/gps.py` but out
      of the live scope for now. Parsing and feature extraction (HRR, effort
      states, trends) live in `src/algorun/sensors/`.
- [ ] Sensor sessions are turned into **natural-language narratives** that go
      through the SAME pipeline as any other text (no shortcut into the KG),
      while a **direct structured mapping** of the same session produces
      ground-truth triples for evaluation.
- [ ] The playlist recommender reads **only from the RDF Knowledge Graph via
      SPARQL** — never directly from raw CSVs. The KG is the single source of
      truth.
- [ ] Code identifiers, data and the report are in **English**; **comments and
      docstrings are in Italian** so both teammates read the implementation
      easily (team decision, 2026-07-05). Theoretical rigor over shortcuts:
      every algorithmic choice must be justifiable w.r.t. the course material.

## Rule 6 — Collaboration workflow (two people, two AIs)

- [ ] **Session start = `git pull`**, always, for both teammates.
- [ ] After every **medium-or-larger task**: update `collab/HANDOFF.md` (and
      `ALGORITHMS.md` when applicable), commit on a **feature branch**, and
      **open a pull request** — no direct commits to `main`.
- [ ] Merge conflicts: **the more reliable version wins** — the one with the
      stronger documented rationale (green tests, guideline compliance,
      cited course algorithm or paper). The resolution and its motivation are
      recorded in `collab/HANDOFF.md`.

## Rule 7 — Code style: essential, symmetric, class-first

- [ ] **Zero pomposity**: the simplest code that solves the problem. No
      speculative abstraction, no unnecessary layers, no cleverness.
- [ ] **Symmetry**: analogous problems get analogous code — interchangeable
      backends share the same interface, parallel modules mirror each other's
      structure.
- [ ] Algorithms follow what was **used and explained in class**; any
      deviation is a conscious, documented choice.

## Rule 8 — Provenance ledger (feeds the final presentation)

- [ ] Every algorithm and its **exact variant**, every **code source of
      inspiration**, and every **scientific paper** behind a design choice is
      recorded in `ALGORITHMS.md` when it enters the codebase, not later.
- [ ] Final deliverable = **code + presentation**; the ledger is the raw
      material for the presentation.

## Session protocol reminder

Before writing any code, also read `CLAUDE.md` (session protocol) and
`collab/HANDOFF.md` (teammate coordination). The handoff protocol is part of
these guidelines.
