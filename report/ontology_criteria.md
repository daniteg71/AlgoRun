# AlgoRun — Criteria for Building the Ontology (step by step)

The exact criteria we follow to build and judge our ontology. Every item is a
checkbox: the ontology is "done" only when all are satisfied. Order matters —
this is the sequence we actually work in (the class method, Block 12).

---

## Step 0 — Scope and purpose (decide before touching Protégé)

- [ ] **One-sentence purpose.** "Classify a runner's physiological state from
      accelerometer + heart-rate and prescribe an acoustic target." Write it
      down; every class must serve it.
- [ ] **Scope boundaries.** In scope: runner, session, phases, intensity
      zones, sensor readings (cadence + heart rate only), acoustic targets,
      songs/genres/playlists. Out of scope: pace/GPS, elevation/barometer,
      social features, nutrition.
- [ ] **Sensors fixed.** Exactly two: accelerometer (→ cadence) and heart-rate
      sensor (→ beats). No pace, no elevation.

## Step 1 — Competency questions (the requirements = the tests)

- [ ] Write the questions the ontology must answer (we have 10, see
      `report/ontology_design.md`).
- [ ] Each competency question becomes a **SPARQL test**
      (`tests/test_competency_questions.py`). If a question can't be answered,
      a class or property is missing.
- [ ] No competency question → no new class. Do not model what nothing asks for.

## Step 2 — Reuse before inventing (NeOn criterion)

- [ ] Check standard vocabularies first. We align (not import) to **SOSA/SSN**
      (sensors/observations), **OWL-Time** (phase intervals), **Music Ontology**
      (BPM/tracks). Reuse is documented with `rdfs:seeAlso`.
- [ ] Invent a term only if no standard fits. Record the decision in
      `ALGORITHMS.md`.

## Step 3 — Foundational backbone (three disjoint cores)

- [ ] Every class descends from one of three IOF-style cores:
      **Agent** / **Process** / **InformationEntity**.
- [ ] The three cores are **mutually disjoint** (`owl:disjointWith`). This is
      what lets the reasoner prove the model is coherent.
- [ ] Test: an individual typed as two cores must make the ontology
      *inconsistent* (`tests/test_ontology_v2.py`).

## Step 4 — Taxonomy criteria (how to place a class)

- [ ] **Is-a only.** `rdfs:subClassOf` means "every X is a Y", nothing looser.
      A `CadenceReading` *is a* `SensorReading` *is an* `InformationEntity`. ✔
- [ ] **Rigidity (OntoClean).** A rigid class (something that is always that
      kind — Runner, Song) may not be subclassed under an anti-rigid/role class.
- [ ] **Sibling disjointness.** Classes that can never overlap are declared
      disjoint (the two reading types; Song/Genre/Playlist).
- [ ] **No orphan classes.** Every class connects to the hierarchy (OOPS! pitfall
      P04). No floating terms.

## Step 5 — Relations (object properties) criteria

- [ ] **Explicit domain and range on every property** (Rule 1). A property with
      no domain/range is forbidden.
- [ ] **Forward + inverse.** Every object property declares its inverse
      (`owl:inverseOf`) — `prescribesTarget` / `prescribedFor`, etc.
- [ ] **Direction encodes meaning.** `Zone prescribesTarget AcousticTarget` is
      not the same as its inverse; pick the reading that matches the reasoning
      chain (sensor → zone → target).
- [ ] **Reuse over duplication.** If a link already exists, reuse it (we dropped
      `forRunner` and reused `performedBy`).

## Step 6 — Attributes (data properties) criteria

- [ ] Each data property has a **domain** (which class carries it) and an
      **xsd range** (decimal, integer, dateTime, string).
- [ ] Units are explicit in the label/comment (`cadenceSpm`, `trackDurationMs`,
      `heartRateBpm`).
- [ ] Value ranges enforced by SHACL where physiology bounds them (HR 25–240,
      cadence 40–260, energy 0–1).

## Step 7 — Individuals / controlled vocabularies

- [ ] Fixed enumerations are individuals: zones Z1–Z5, phases, workout types,
      acoustic targets.
- [ ] Growing vocabularies (genres, workout types) are also **SKOS concepts**
      in a `skos:ConceptScheme`, so they extend without changing axioms.
- [ ] Rich `skos:altLabel` synonyms on everything — they feed the NER
      dictionary and make the dataset's "implicit" tier solvable.

## Step 8 — Constraints (SHACL = the constraint gate)

- [ ] One subject-shape + one object-shape per domain/range pair.
- [ ] Value bounds for measured quantities.
- [ ] **Domain safety rules** as SPARQL-SHACL: cadence step ≤ 5 %, no energetic
      target above safe-max HR, emergency → calming target.
- [ ] SHACL runs with **inference OFF** (closed world), so violations are
      *rejected*, not classified away.

## Step 9 — Validation (three levels, Block 13)

- [ ] **Functional:** all competency-question SPARQL tests pass.
- [ ] **Logical:** the reasoner (HermiT) reports the ontology consistent, and a
      deliberately-broken ABox inconsistent.
- [ ] **Quality:** OOPS! pitfall scan is clean; OntoClean taxonomy check passes.
      Recorded in `report/ontology_eval.md`.

## Step 10 — Naming and hygiene conventions

- [ ] Classes `UpperCamelCase`, properties `lowerCamelCase`, individuals
      `UpperCamelCase`. Consistent, English, singular class names.
- [ ] Every term has an `rdfs:label`; non-obvious terms have an `rdfs:comment`.
- [ ] One namespace (`ar:`), one file, hand-written Turtle kept in git;
      Protégé-compatible.
- [ ] `owl:versionInfo` bumped on every meaningful change.

---

## The acceptance checklist (the ontology is "done" when…)

1. Every competency question is answered by a passing SPARQL test.
2. Every class descends from a core; cores are disjoint; no orphans.
3. Every object property has domain, range and an inverse.
4. Every data property has domain and an xsd range; bounded ones have SHACL.
5. Reasoner: consistent; broken ABox: inconsistent.
6. OOPS!: no critical/important pitfalls.
7. Only the two in-scope sensors (cadence, heart rate) appear.
8. `ALGORITHMS.md` records every reused vocabulary and cited source.
