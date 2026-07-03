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
