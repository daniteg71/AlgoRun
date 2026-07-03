# CLAUDE.md — AI Session Protocol for AlgoRun

This repository is developed by a **2-person team**, each member working with
their own AI assistant. This file defines the mandatory protocol for every AI
session in this repo.

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
- Python ≥ 3.9 (3.11+ for M4 training). Source in `src/algorun/`; tests in
  `tests/` (pytest).
- `data/sensor/` and `data/music/` stay out of git; `data/synthetic/` is a
  course deliverable and stays in.
