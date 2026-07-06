# CLAUDE.md — AI Session Protocol for AlgoRun

This repository is developed by a **2-person team**, each member working with
their own AI assistant. This file defines the mandatory protocol for every AI
session in this repo.

## The objective — always keep this end-to-end vision in mind

AlgoRun is a **text-driven, ontology-governed running-music recommender**
(no wearables required). Every piece of code serves this loop — see
`ARCHITECTURE.md` for the full design and the `[NOW]/[STAR]/[BENCH]/[EXT]` tags:

1. **NLP dispatcher.** A short user utterance → a *regime*
   (quantitative | qualitative) + slots (speed, duration, mood, genre). Shipped
   model: dictionary + regex; heavier models are benchmark contenders only.
2. **Ontology → target + dynamic weights.** The regime decides how the ontology
   derives the acoustic target (BPM/energy bands) and which features dominate
   the score. SHACL is the constraint gate — no triple enters the KG without it.
3. **Dynamic Vector Scoring.** Rank catalog tracks by weighted cosine/distance
   to the target over bpm/energy/valence/danceability (regime weights), plus a
   genre semantic-distance term. The recommender reads only from the KG via
   SPARQL.
4. **Sliding-Window memory + Spotify.** A deque of recent tracks keeps the
   sequence coherent; the winning track is played via spotipy.

The graded backbone is offline: synthetic tiered corpus → Data Refinery → KG →
benchmark. Live GPS/HR sensors and a real-time loop are a **north-star [STAR]**,
not a requirement. Whenever a design decision is unclear, choose the option that
best serves this loop — and always respect `ARCHITECTURE.md` and `GUIDELINES.md`.

## FIRST ACTION of every session (mandatory, before anything else)

1. **`git pull`** — always sync with the remote first, so you see the
   teammate's latest work. This applies to BOTH teammates, every session.
2. Read `collab/HANDOFF.md`.
3. **Output to the user, as the very first thing in the session:**
   - the pending **TODOs** the other teammate left for them,
   - the **ideas** and **open questions** from the latest entries they have
     not yet seen.
4. Only then proceed with the user's request.

This applies even if the user's first message is about something else —
surface the handoff summary first, then continue.

## Before writing ANY code

- Read `ARCHITECTURE.md` — the canonical design document (what AlgoRun is and
  how we build it). Its `[NOW]/[STAR]/[BENCH]/[EXT]` tags tell you what to build
  now vs. what is north-star, benchmark-only, or an external constraint. Do not
  build a `[STAR]` (sensors, real-time) as if it were required.
- Read `GUIDELINES.md` and verify the applicable checklists. Those rules are
  binding: pipeline stage order, 70/15/15 split, 4 complexity tiers,
  generator/validator dissociation, SHACL-before-RDF, graph-based P/R/F1
  benchmarking.
- If the requested change would violate a guideline, stop and tell the user
  which rule conflicts instead of implementing it.

## After completing any medium-or-larger task (mandatory)

A "medium task" is anything beyond a trivial fix: a milestone, a new module,
a meaningful refactor. When one is done:

1. Update the communication files: new entry in `collab/HANDOFF.md`, and
   `ALGORITHMS.md` if any algorithm, code source or paper was used.
2. Commit on a **feature branch** (`m3-baseline-pipeline`, `fix-shacl-gate`,
   ...) — **never commit directly to `main`**.
3. Push the branch and **open a pull request automatically** (`gh pr create`
   — if the `gh` CLI is missing, push the branch and tell the user to open
   the PR from the printed GitHub link).

## Merge conflicts

When a conflict arises between the two teammates' work, **the more reliable
version wins**: the one backed by the stronger rationale — green tests,
compliance with `GUIDELINES.md`, a cited source or course algorithm. The
resolver documents the decision and its motivation in `collab/HANDOFF.md`.
Never resolve a conflict by silently keeping "mine".

## Code style (binding)

- **Zero pomposity.** Essential code, the simplest thing that works. No
  speculative abstractions, no clever tricks, no decorative layers.
- **Work by symmetry:** same problem shape → same code shape. Modules that do
  analogous jobs (e.g., the two NER backends) expose identical interfaces.
- Prefer the algorithms **used and explained in class** (see `GUIDELINES.md`
  and the Block PDFs); deviations must be justified in `ALGORITHMS.md`.

## Provenance ledger

Every algorithm, its exact variant, every code source of inspiration and
every scientific paper consulted MUST be recorded in `ALGORITHMS.md` at the
moment it enters the codebase — this feeds the final presentation (final
deliverable = code + presentation).

## Working conventions

- Language: chat with the user may be in Italian; **all code, comments, docs,
  data and the report are in English**.
- Project plan and milestones: see `README.md`. Course rules: `GUIDELINES.md`.
- Python ≥ 3.9 works end-to-end (incl. Transformer training on Apple MPS;
  on 3.9 pin `spacy<3.8`). Source in `src/algorun/`; tests in `tests/` (pytest).
- Heavy trainings (e.g. roberta-base) do NOT run on the user's laptop —
  prepare a Colab snippet instead (see README).
- `data/sensor/` and `data/music/` stay out of git; `data/synthetic/` is a
  course deliverable and stays in.
