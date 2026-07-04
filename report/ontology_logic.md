# AlgoRun — How the Ontology Works and Why (the full logic)

This is the theoretical spine of the project. It explains *how* the ontology
classifies and reasons, and *why* every choice is made. It is written to be
read alongside `ontology/algorun.owl` and is the main source for the final
presentation.

---

## 0. The core idea: model physiological STATES, not steps

The naive way to see a run is a sequence of footsteps. AlgoRun instead models a
run as a trajectory through **physiological states**. The AI never asks "what
song title?" — it asks "what state is the runner in, and what acoustic
stimulus does that state require?". The ontology is the formal description of
those states and of the rules that connect them to sound.

This is what turns the project from a script into **Knowledge Engineering**
(the AI-LAB requirement): the domain rules live in a logical-symbolic model
(OWL classes + SHACL constraints) that a reasoner can inspect and validate,
not inside `if/elif` branches. The `if/elif` version would ship faster; the
ontology is the academically correct way to *formalize and prove* the domain.

---

## 1. The three-core backbone (why the taxonomy is shaped this way)

Following the class method (Block 12, IOF-style foundation), every class hangs
under one of three **mutually disjoint** cores:

- **Agent** — who acts: `Runner`.
- **Process** — what happens in time: `WorkoutSession`, `TrainingPhase`.
- **InformationEntity** — what describes/records/prescribes: `SensorReading`,
  `IntensityZone`, `AcousticTarget`, `ActionPriority`, `Song`, `Genre`,
  `Playlist`.

Disjointness (`owl:disjointWith`) is not decoration: it lets the reasoner
*prove* the model is coherent. A song can never be a process, a heart-rate
reading can never be an agent. When we later feed noisy, LLM-extracted data
into the graph, these axioms are the first line that catches nonsense.

---

## 2. The reasoning chain (how the AI actually "thinks")

The whole system is one inference chain the reasoner walks left to right:

```
sensor HR  ──►  IntensityZone  ──►  AcousticTarget  ──►  (vector search)  ──►  Song
             (Karvonen zones)   (prescribesTarget)      (KNN on BPM/energy)
```

Concretely:

1. A `HeartRateReading` is recorded in the session (`recordsReading`).
2. Its value is classified into an `IntensityZone` Z1–Z5 (`readingInZone`),
   using the Karvonen % HRmax bands.
3. The zone **prescribes an `AcousticTarget`** (`prescribesTarget`). This is
   the heart of the ontology: a zone is not just a number, it *demands* a
   specific kind of sound.
4. The `AcousticTarget` is a *region* in (BPM, energy, valence, duration)
   space — **not a song**. Vector search (step 4 of the project objective)
   then finds the nearest real track.

Training phases connect to the same chain: `TrainingPhase --targetsZone-->
IntensityZone --prescribesTarget--> AcousticTarget`. So whether the driver is
the live sensor (bottom-up) or the planned phase (top-down), both routes land
on the same target. This symmetry is deliberate.

---

## 3. The classification: training zones × music (the mapping table)

The physiological key is the **intensity zone**. Each zone prescribes one
acoustic target:

| Workout type | HR zone | Energy | BPM target | Musical character |
|---|---|---|---|---|
| **Recovery run** | Z1 (50–60% HRmax) | 0.1–0.3 | **90–110** | Ambient, chill-out, downtempo |
| **Easy / Long run** | Z2 (60–70%) | 0.4–0.6 | **120–130** | Deep house, pop, podcast-friendly |
| **Tempo / Threshold** | Z3–Z4 (80–90%) | 0.6–0.8 | **130–150** | Techno, drum & bass, steady rhythm |
| **Intervals / HIIT** | Z5 (90–100%) | 0.8–1.0 | **150+** | Hard techno, metal, dubstep, high-drive |

These are the `AcousticTarget` individuals in the ontology (`RecoveryTarget`,
`EasyTarget`, `ThresholdTarget`, `IntervalTarget`).

---

## 4. The theory behind the numbers (the important part)

### 4.1 Entrainment (why beat-matching works)
The motor system spontaneously locks onto an auditory rhythm — *entrainment*.
Runners synchronize step rate to the beat when the beat is within ~2–3% of
their preferred cadence (Van Dyck et al. 2015). Synchronizing footfall to the
beat can reduce oxygen consumption by up to ~7% and smooth the stride, lowering
joint impact.

### 4.2 The 1:1 vs half-time trick (why recovery is 90–110, not 160)
A runner's cadence sits around 150–180 steps per minute. So why does the
recovery target say 90–110 BPM? Because the foot can lock to the beat in **two
ratios**:

- **1:1** — one step per beat. Used at high intensity, where the track is a
  *metronome* driving pace (Threshold/Interval: 130–180 BPM ≈ cadence).
- **2:1 (half-time)** — one step every two beats. Used at low intensity, where
  a 95 BPM track still supports a ~190 spm... no: it supports a calm, unforced
  gait while keeping arousal low. Recovery music must *calm* the runner, so we
  pick a low BPM and let the body entrain in half-time.

So the rule is not "BPM = cadence" everywhere. **At low intensity we optimize
arousal (calm), at high intensity we optimize synchronization (drive).** That
is the single most important idea in the whole mapping.

### 4.3 Arousal and dissociation
Fast, loud music raises heart rate, respiration and arousal (Terry &
Karageorghis 2011); it also acts as a *dissociative distractor* that lowers
perceived exertion (RPE). Two consequences we encode:
- Use high-energy music to push in Z4–Z5.
- **Danger:** masking fatigue too long invites overuse injury. The system must
  not let a runner ignore critical body signals → the safety constraints (§5).

### 4.4 The ceiling — when NOT to push tempo
Above ~75–80% of aerobic capacity, music becomes ineffectual at reducing RPE,
and preference for ever-faster tempo flattens (the "ceiling" / "Clarke dip",
Karageorghis & Terry 2009). Practically: past a point, silence or a steady
metronome beats an even faster track. We do not chase BPM past the Interval
band.

---

## 5. "When a song is too fast" — the safety logic

The ontology does not only pick a target; it **refuses unsafe ones**. Three
SPARQL-SHACL constraints (in `ontology/shapes.ttl`) act as the constraint gate:

1. **Cadence guard (`CadenceStepShape`).** The applied target BPM must not
   exceed the runner's *current cadence* by more than **5%**. Increasing step
   rate 5–10% reduces joint load, but a big abrupt jump causes fatigue and
   injury (Heiderscheit et al. 2011). This blocks the classic failure: runner
   at 140 spm, system tries to fire a 180 BPM track.
2. **Critical-HR guard (`CriticalHeartRateShape`).** At or above the runner's
   `safeMaxHeartRateBpm`, any energetic target (> 140 BPM) is rejected — the
   system must force a calming target to bring HR and stress hormones down.
3. **Emergency guard (`EmergencyTargetShape`).** If the state is escalated to
   `EmergencyPriority`, the applied target must be ≤ 140 BPM.

Note the division of labour: **the ontology decides *what* and *how urgent*;
the M5 Python server decides *when* to act.** The server adds the control-loop
behaviour that keeps the experience from being "schizophrenic":

- **Hysteresis (smoothing):** decisions use a 1–2 min moving average of HR, so
  a 10-second spike is ignored.
- **Playback lock (cooldown):** when a track starts, a 2–3 min lock blocks
  song changes so the track can develop.
- **Panic button (immediate skip):** when the ontology sets
  `EmergencyPriority`, the controller **bypasses the lock** and calls
  `sp.next_track()` for a hard cut to a calming track.

`safeMaxHeartRateBpm` is the **emergency** threshold, deliberately *above* the
normal training zones — Z5 (90–100% HRmax) is legitimate hard training with a
150+ target; the emergency fires only past the runner's personal danger line
(default: **93% HRmax**, or a clinician-set absolute value per runner).

---

## 6. Why this scores well at the exam

- **Symbolic validator over a probabilistic model** (course Architecture 4):
  GLiNER/LLM propose, SHACL disposes. The safety rules are *proven*, not hoped.
- **Reasonable ontology:** the reasoner (HermiT) confirms consistency; the
  disjoint cores make bad data provably inconsistent.
- **Every threshold is cited** (see `report/music_science.md`), and where the
  evidence is thinner (150–180 band) we say so instead of overclaiming.

---

## References

See `report/music_science.md` for the full citation list (Terry &
Karageorghis 2011; Karageorghis & Terry 2009; Van Dyck et al. 2015;
Heiderscheit et al. 2011; Tanaka et al. 2001; Karvonen et al. 1957; Szmedra &
Bacharach 1998) plus practitioner BPM guides. Google Scholar entry point for
this topic: search *"Training Intensity Zones Music Synchronization"*.
