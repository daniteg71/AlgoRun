# AlgoRun Ontology — Design Document (v0.2 plan)

Method: the one taught in class (Block 12, Logistic Ontology — Conception &
Dataset), which is the Grüninger & Fox competency-question methodology plus
an upper-ontology foundation (IOF Core style) and an OWL+SKOS split.

## 1. Methodology (class-taught, Block 12)

1. **Foundation on three disjoint cores** (IOF Core style): the class
   ontology used `MaterialEntity` / `Agent` / `Process`, mutually disjoint
   ("a process is not a physical object, an agent is not a location").
2. **Domain classes as subclasses of the cores**, with explicit mutual
   disjointness between siblings.
3. **Forward properties each with a declared inverse.**
4. **OWL for the axioms, SKOS for taxonomies that grow over time**
   (class example: product family/subfamily; our case: music genres,
   workout types).
5. **Conception driven by client interviews → competency questions**:
   what must the ontology be able to answer? Each competency question
   becomes a SPARQL test.

## 2. Competency questions (our "client" is the runner)

CQ1. Which songs suit the *sprint* phase of an *interval* session in zone Z5?
CQ2. Which BPM should play when the runner's cadence is ~172 spm?
CQ3. Which playlist was built for a given workout session?
CQ4. In which intensity zone was the heart rate during a given phase?
CQ5. Which genres does the runner prefer for *recovery* runs?
CQ6. Which sessions did a runner perform, and of which workout type?
CQ7. Which songs in the catalog match zone Z3 AND belong to a preferred genre?
CQ8. What phase sequence (warm-up → ... → cool-down) does a session have,
     and which zone does each phase target?
CQ9. Which readings (heart rate, cadence) were recorded in a session?
CQ10. Given a workout type, which BPM curve should the playlist follow?

Acceptance rule: v0.2 is done when every CQ is answerable by a SPARQL query
against a sample KG — these queries become pytest cases (Grüninger & Fox:
competency questions are the ontology's requirements AND its test suite).

## 3. Core structure (v0.2)

Three disjoint cores, IOF-style, adapted to our domain:

```
ar:Agent                     # who acts
 └─ ar:Runner

ar:Process                   # what happens in time
 ├─ ar:WorkoutSession
 └─ ar:TrainingPhase         # WarmUp, Steady, Sprint, CoolDown

ar:InformationEntity         # what describes/records/prescribes
 ├─ ar:SensorReading         # HeartRateReading, CadenceReading
 ├─ ar:MusicEntity           # Song, Genre, Playlist
 └─ ar:IntensityZone         # Z1..Z5 (classification of effort)
```

Disjointness axioms (new in v0.2 — v0.1 had none):
- `Agent ⊥ Process ⊥ InformationEntity` (mutually);
- sibling reading types mutually disjoint;
- `Song ⊥ Genre ⊥ Playlist`.

SKOS layer (new in v0.2, per Block 12):
- `ar:WorkoutTypeScheme` and `ar:GenreScheme` as `skos:ConceptScheme`;
  workout types and genres become `skos:Concept`s with `skos:prefLabel` /
  `skos:altLabel` / `skos:broader`. Rationale: these taxonomies grow (new
  genres arrive with the music catalog; new workout types with training
  plans) without touching the OWL axioms. OWL classes stay for things with
  logical constraints; SKOS for evolving vocabularies.

Properties: every forward property gets an inverse (v0.1 had 4/14 —
completed in v0.2), e.g. `suitsPhase/hasSuitedSong`,
`hasGenre/isGenreOf`, `readingInZone/zoneOfReading`.

New property (enables CQ5/CQ7): `prefersGenre (Runner → Genre)` with
inverse `preferredBy`.

## 4. Theory behind it (for the report/presentation)

- **Ontology = TBox + ABox** (Description Logics). TBox: terminological
  axioms (`Runner ⊑ Agent`, domain/range); ABox: assertions
  (`performsSession(danny, session1)`). OWL 2 DL corresponds to the DL
  **SROIQ(D)**; semantics is model-theoretic: an interpretation
  I = (Δ^I, ·^I) maps classes to subsets of Δ and properties to binary
  relations; an axiom holds iff it holds in every model.
- **Open World vs Closed World**: OWL/RDFS reasoning is open-world —
  `rdfs:domain`/`range` *classify* (a violating subject is inferred into
  the domain class, cf. our M1 test finding); **SHACL is closed-world
  validation** — it checks the data as-is and rejects. That is why the
  pipeline validates with SHACL (inference off) before RDF assembly.
- **RDF graph** = set of triples ⊆ (IRI ∪ B) × IRI × (IRI ∪ B ∪ Literal);
  SPARQL evaluates basic graph patterns by subgraph matching.

## 5. Reading list

Class material first (Rule 7):
1. **Block 12** — ontology conception method (cores, disjointness,
   inverses, OWL+SKOS, client interview). Our blueprint.
2. **Block 13** — ontology & dataset evaluation.
3. **Blocks 05–11** (Pokemon Ontology series) — worked example of
   ontology → NLP extraction → transformer benchmarking.
4. **Block 04(B) Miscellaneous** — `LOTROntology.owl`: a complete OWL file
   from class to imitate structurally.
5. **Block 14** — pipeline mandate (already codified in GUIDELINES.md).

External canon:
- Noy & McGuinness (2001), *Ontology Development 101* (Stanford KSL) — the
  practical 7-step guide; closest single text to what Block 12 does.
- Grüninger & Fox (1995), *Methodology for the Design and Evaluation of
  Ontologies* — competency questions.
- Gruber (1993), *A translation approach to portable ontology
  specifications* — the classic definition ("explicit specification of a
  conceptualization").
- W3C **OWL 2 Primer** and **SKOS Primer** — the working references.
- W3C **SHACL Recommendation** (2017) — the constraint language.
- Baader et al., *The Description Logic Handbook* — chapters 2–3 for the
  math (syntax/semantics of DLs, tableau reasoning).
- Arp, Smith & Spear (2015), *Building Ontologies with Basic Formal
  Ontology* — the upper-ontology philosophy behind IOF Core.

Note: the two course textbooks (Szeliski; Zhang et al. *Dive into Deep
Learning*) do not cover ontologies — the ontology "book" for this project
is the DL Handbook + the W3C primers above.

## 6. v0.1 → v0.2 gap list (implementation ticket)

- [ ] Add the three cores + `owl:disjointWith` axioms.
- [ ] Move IntensityZone under InformationEntity; keep Z1–Z5 individuals.
- [ ] Complete inverses for all object properties.
- [ ] Add `prefersGenre`/`preferredBy` + SHACL shapes.
- [ ] Add SKOS concept schemes for WorkoutType and Genre (keep the OWL
      individuals, add `skos:Concept` typing + scheme membership so the
      pipeline label dictionary is unchanged).
- [ ] Write the 10 CQ SPARQL queries as pytest cases against a fixture KG.
- [ ] Update ALGORITHMS.md (methodology + sources above).
