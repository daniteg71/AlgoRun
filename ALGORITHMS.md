# ALGORITHMS.md — Provenance Ledger

Every algorithm (with its exact variant), every code source of inspiration
and every scientific paper behind a design choice, recorded **when it enters
the codebase** (GUIDELINES.md Rule 8). This ledger is raw material for the
final presentation (deliverable = code + presentation).

Format per entry: what / variant / where in the codebase / source.

## Algorithms in use

| Algorithm | Variant used | Where | Source |
|---|---|---|---|
| Dictionary-based entity matching | Longest-string-match-first over OWL labels + SKOS altLabels | `src/algorun/ontology/loader.py` (`label_dictionary`) | Course Block 14, "Classical Rule-Based" entity detection |
| SHACL constraint validation | Node shapes per domain/range pair, `inference="none"`, ontology merged into data graph | `ontology/shapes.ttl`, `tests/test_shacl_gate.py` | W3C SHACL Recommendation (2017); course Block 14 "Semantic Grounding" |
| Stratified random split | Per-tier shuffle + 70/15/15 cut, fixed seed 42 | `src/algorun/datagen/generator.py` (`split_records`) | Course Block 14 requirement (70/15/15) |
| Template-based synthetic text generation | LLM-authored templates instantiated with ontology surface forms; gold spans computed by substring search | `src/algorun/datagen/templates.py`, `generator.py` | Course Block 14, "Synthetic Data Generation via LLMs" (tiered complexity) |
| Heart-rate intensity zones | 5-zone model (Z1–Z5) | `ontology/algorun.owl` (IntensityZone individuals) | Karvonen, Kentala & Mustala (1957), *Ann. Med. Exp. Biol. Fenn.* 35(3) |
| Ontology conception | Three disjoint IOF-style cores (Agent/Process/InformationEntity), forward+inverse properties, OWL+SKOS split, competency-question driven | `ontology/algorun.owl` | Course Block 12; Grüninger & Fox (1995); Noy & McGuinness (2001) |
| Vocabulary reuse by alignment | `rdfs:seeAlso`/`subClassOf` bridges to SOSA/SSN (sensors), OWL-Time (phases), Music Ontology (BPM) — no external imports | `ontology/algorun.owl` | Suárez-Figueroa et al. (2015) NeOn; Haller et al. (2019) SOSA/SSN; Raimond et al. (2007) Music Ontology |
| Competency-question evaluation | 10 CQs as SPARQL over a sample KG (functional evaluation) | `tests/test_competency_questions.py`, `evaluation.py::sample_kg` | Course Block 13; Grüninger & Fox (1995) |
| OWL DL reasoning (consistency) | HermiT via owlready2; disjoint-core violation → inconsistent | `src/algorun/ontology/evaluation.py`, `tests/test_ontology_v2.py` | Course Block 13; Baader et al., *DL Handbook* |
| Ontology quality diagnosis | OOPS! pitfall scan + informal OntoClean taxonomy check | `tests/test_competency_questions.py` | Poveda-Villalón et al. (2014) OOPS!; Guarino & Welty OntoClean |
| Per-zone BPM/energy targets | 4 AcousticTargets indexed by effort state: Low 90–110, Target 120–130, High 130–150, VeryHigh 150–180; 1:1 vs half-time synchronization logic | `ontology/algorun.owl`, `ontology/algorun.owl` (comments) | Terry & Karageorghis (2011); Karageorghis & Terry (2009); Van Dyck et al. (2015); practitioner BPM guides |
| Cadence-safety constraint | SPARQL-SHACL: applied BPM ≤ 1.05 × current cadence | `ontology/shapes.ttl` (`CadenceStepShape`) | Heiderscheit et al. (2011) |
| Critical-HR & emergency guards | SPARQL-SHACL: no target > 140 bpm at/above safe max HR or under EmergencyPriority | `ontology/shapes.ttl` | Terry & Karageorghis (2011); Szmedra & Bacharach (1998) |
| HRmax / zone models | Tanaka (208−0.7·age), Fox (220−age), Karvonen HR reserve, 5-zone % HRmax | `ontology/algorun.owl` (comments) | Tanaka et al. (2001); Fox et al. (1971); Karvonen et al. (1957) |
| Control-system smoothing (planned M5) | HR moving average (hysteresis) + playback lock + emergency bypass skip | M5 server | standard control-systems practice; documented in `ontology/algorun.owl` (comments) |
| Heart Rate Reserve (HRR) | (HR − rest)/(max − rest), clipped [0, 1.2] | `src/algorun/sensors/physiological_state.py` (`compute_hrr`) | Karvonen et al. (1957) |
| Effort classification | Threshold bins on HRR (Low<0.40, Target<0.70, High<0.85, VeryHigh≥0.85) | `physiological_state.py` (`classify_effort`) | Karvonen zones (thresholds chosen by team) |
| HR-trend estimation | Least-squares linear slope (`np.polyfit` deg=1) over the window; ±0.05 bpm/s → Increasing/Stable/Decreasing | `physiological_state.py` (`calculate_linear_slope`, `classify_trend`) | standard linear regression |
| Sliding-window featurization | 30 s window, 5 s stride; per-window mean/std/min/max/delta + HRR + trend | `src/algorun/sensors/build_dataset.py` | standard time-series windowing |
| Simulated BPM sessions | Piecewise-linear phase ramps + sinusoidal oscillation + Gaussian noise, seed 42 | `src/algorun/sensors/generate_simulated_bpm.py` | team (synthetic sensor data for offline dev) |
| Sensor→ontology bridge | effort → RDF → SHACL → SPARQL target + 93%-HRmax safety override | `src/algorun/pipeline.py` | course Block 14 (Semantic Grounding); Terry & Karageorghis (2011) |
| NER (baseline) | Rule-based dictionary matching, longest-match-first over ontology labels | `src/algorun/nlp.py` (`dictionary_extract`) | course Block 14 "Classical Rule-Based" |
| NER (advanced) | GLiNER zero-shot (no fine-tuning), labels mapped to ontology classes | `src/algorun/nlp.py` (`gliner_extract`) | Zaratiana et al. (2024) GLiNER, NAACL; GLiNER2 (arXiv 2507.18546) |
| Quantity parsing | Regex for value+unit (duration, speed) — NER finds the span, regex parses the number | `src/algorun/nlp.py` (`parse_quantities`) | standard NER+regex hybrid practice |
| Qual/quant routing | One `if`: declared value → quantitative target; else → defer to HR sensors | `src/algorun/nlp.py` (`classify`) | project design (dual-mode grounding) |
| Speed → cadence → BPM | Linear cadence regression (134 + 2.9·kmh, clamp 150–190) then 1:1 / half-time entrainment | `src/algorun/nlp.py` (`target_bpm`) | Van Dyck et al. (2015); cadence-vs-pace literature (155–186 spm ranges) |
| Prompt grounding | GLiNER/dict spans + quantities → RDF triples for the A-Box, SHACL-validated | `src/algorun/nlp.py` (`ground`) | course Block 14 (grounding + SHACL gate) |
| Entity extraction P/R/F1 | Micro-averaged over an annotated prompt gold set. **Measured 2026-07-05: dictionary F1 0.947 vs GLiNER-small 0.20** — on a closed ontology vocabulary the rule-based baseline dominates; GLiNER's value is out-of-vocabulary phrasing (to retest with gliner_medium on Colab and an OOV gold set) | `src/algorun/nlp.py` (`evaluate`), `tests/test_nlp.py` | course Block 14 evaluation framework |
| GPS speed from Location.csv | Sensor Logger `speed` column preferred; fallback Haversine d=2R·asin(√a) between fixes; accuracy filter ≤20 m; moving-average smoothing; kmh/pace conversions; speed→cadence→BPM reuse | `src/algorun/sensors/gps.py`, `tests/test_gps.py` | Haversine (standard geodesy); Van Dyck et al. (2015) for the BPM step |
| Tokenization + lemmatization | spaCy `en_core_web_sm` (3.7.2 — pinned below 3.8 for Python 3.9 compatibility, thinc≥8.3.12 needs 3.10+) | `src/algorun/refinery.py` (`tokenize`) | Course Block 14 pipeline order; Honnibal & Montani, spaCy |
| Trigger-word relation extraction | Multi-word triggers matched on LEMMA within a 4-token slack (not required contiguous — the generator's own phrasing splits them, e.g. "includes A HARD phase"), then subject/object paired by nearest domain/range-compatible entity within ±10 tokens. **Measured on test.jsonl (held-out): overall P=1.00 R=0.137 F1=0.241; per-relation R=1.00 on hasPhase/targetsEffort (trigger genuinely adjacent to entity), R=0.00 elsewhere** — either the relation's own trigger phrase never appears near the entity in this corpus (hasWorkoutType, hasEffortState — co-occurrence-implied, not trigger-cued) or an endpoint is outside the closed ontology vocabulary (song/playlist/genre/runner names, un-mentioned implicit readings): ~60% of gold triples fall in this second, structural case. `long_distance` tier: R=0.00 (entities too far apart for the ±10-token window — the documented "brittle on complex sentences" limit, now with a number). Precision is 1.00 everywhere it fires: the domain/range filter never proposes a wrong pair | `src/algorun/refinery.py` (`extract_relations`) | Course Block 14, "SpaCy Baseline" (documented limitations); course "pairwise, ontology-constrained" option instead of GLiREL |
| Graph P/R/F1 evaluation | Triple-level TP/FP/FN, predicted vs. ground-truth graph, overall + per tier + per relation type; implicit (un-mentioned) gold nodes canonicalized by type (one WorkoutSession per document, matching the generator) | `src/algorun/refinery.py` (`evaluate_on_dataset`) | Course Block 14, "Evaluation Framework" (Phase 6: Knowledge Graph Assembly) |
| Label-guided NER | GLiNER, labels derived from ontology | M4 | Zaratiana et al. (2024), *GLiNER: Generalist Model for NER using Bidirectional Transformer*, NAACL 2024, arXiv:2311.08526 |
| Relation candidate generation | **Decision: NO GLiREL** — pairwise candidates constrained by ontology domain/range + trigger words (course "GLiREL / pairwise" Architecture A). Our relations are schema-determined; GLiREL adds a heavy immature dependency for nothing | M3/M4 | Course Block 14 (pairwise option); decision recorded 2026-07-05 |
| Supervised binary relation validator | Fine-tuned DistilBERT and RoBERTa-base, sentence + candidate pair → VALID/INVALID | M4 | Sanh et al. (2019) arXiv:1910.01108; Liu et al. (2019) arXiv:1907.11692; course "Generator→Validator" architectural shift |
| Music–exercise tempo matching | Song BPM ≈ target cadence (or half-time); energy scaled to intensity zone | M5 | Karageorghis & Priest (2012), *Music in the exercise domain: a review and synthesis*, Int. Rev. Sport Exerc. Psychol. |
| Cadence estimation from accelerometer | Peak detection on vertical acceleration magnitude | M5 | Standard signal-processing practice (documented in report) |
| Fuzzy string matching | RapidFuzz token-based ratio for playlist→catalog join | M5 | RapidFuzz library docs |

## Code sources of inspiration

- Course Block 14 PDF (Avola-Lezochè, AI-LAB 2025/2026) — pipeline order,
  architecture paradigms A/B/C, evaluation framework. Primary source.
- Course Blocks 05–13 (Pokemon/Logistic Ontology series) — worked examples of
  ontology-driven NLP extraction and benchmarking.
- rdflib / pyshacl official documentation — graph handling and validation API.
- No external code was copied; all modules written from scratch against the
  course specifications.

## Notes for the presentation

- SHACL-vs-RDFS-inference finding (M1): with RDFS inference on, domain/range
  axioms *classify* violating subjects instead of rejecting them; SHACL with
  inference off is what makes the ontology a real constraint gate. Concrete,
  demo-able theory point.
- Verify arXiv IDs/venues above against the originals before the final
  presentation.
