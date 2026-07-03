# CLAUDE.md — AI Session Protocol for AlgoRun

This repository is developed by a **2-person team**, each member working with
their own AI assistant. This file defines the mandatory protocol for every AI
session in this repo.

## FIRST ACTION of every session (mandatory, before anything else)

1. Read `collab/HANDOFF.md`.
2. **Output to the user, as the very first thing in the session:**
   - the pending **TODOs** the other teammate left for them,
   - the **ideas** and **open questions** from the latest entries they have
     not yet seen.
3. Only then proceed with the user's request.

This applies even if the user's first message is about something else —
surface the handoff summary first, then continue.

## Before writing ANY code

- Read `GUIDELINES.md` and verify the applicable checklists. Those rules are
  binding: pipeline stage order, 70/15/15 split, 4 complexity tiers,
  generator/validator dissociation, SHACL-before-RDF, graph-based P/R/F1
  benchmarking.
- If the requested change would violate a guideline, stop and tell the user
  which rule conflicts instead of implementing it.

## LAST ACTION of every session (or after completing a milestone)

Append a new entry at the **top** of `collab/HANDOFF.md` (below the header),
using the entry template defined there: author, date, what was done, ideas
that came up, TODOs for the other teammate, open questions. Commit it together
with the session's work.

## Working conventions

- Language: chat with the user may be in Italian; **all code, comments, docs,
  data and the report are in English**.
- Every milestone ends with a git commit (and a HANDOFF entry).
- Project plan and milestones: see `README.md`. Course rules: `GUIDELINES.md`.
- Python ≥ 3.11. Source lives in `src/algorun/`; tests in `tests/` (pytest).
- Never put datasets or model weights in git; `data/` contents (except
  `.gitkeep` and small samples) and `models/` are gitignored.
