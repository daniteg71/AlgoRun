# AlgoRun — Music & Health Science (evidence behind the rules)

This document grounds every numeric threshold in the ontology. It feeds the
final report/presentation and is cited from `ALGORITHMS.md`.

## 1. Why an ontology and not `if/elif`?

Honest answer: a dozen `if heart_rate > 160: play_fast()` would ship an app in
two hours. We use an ontology because this is the AI-LAB exam (Avola & Lezochè):
the goal is to demonstrate **Knowledge Engineering** — a logical-symbolic
validator (the course "Architecture 4" / Generator→Validator shift) governing
an AI system, with domain constraints formalized in OWL + SHACL rather than
buried in procedural code. The `if/elif` version is easier; the ontology is the
academically correct way to formalize and *prove* the domain constraints.

## 2. Theoretical pillars (Terry & Karageorghis, 2011)

Source: Terry, P. C. & Karageorghis, C. I. (2011). *Chariots of Fire: The Role
of Music in Sport and Exercise* (book chapter). Key claims we rely on:

- **Dissociation & fatigue.** Music lowers perceived exertion (RPE) by acting
  as a sensory distractor against fatigue signals. Caveat we encode as a
  safety rule: masking pain too long risks overuse injury — the system must not
  let a runner ignore critical body signals.
- **Motor synchronization (cadence ↔ BPM).** Humans spontaneously align step
  rate to musical tempo; synchronizing footfall to the beat improves running
  economy and can reduce joint impact forces (the Gebrselassie / "Scatman"
  world-record example is discussed in the chapter).
- **Arousal.** Fast, loud, high-tempo music increases heart rate, respiration
  and arousal — motivational music is generally > 120 bpm (Karageorghis).
- **Tempo–HR preference is quartic, with a ceiling.** Karageorghis & Terry
  (2009): preferred tempo rises with intensity but flattens; above ~80% maxHRR
  there is a ceiling/"Clarke dip". The familiar tempo band is **80–140 bpm**.

## 3. BPM mapping (ontology AcousticTarget individuals)

Indexed by intensity zone (the physiological key). These are the
`RecoveryTarget` / `EasyTarget` / `ThresholdTarget` / `IntervalTarget`
individuals in the ontology.

| Workout type | HR zone | Energy | BPM | Musical character |
|---|---|---|---|---|
| Recovery run | Z1 (50–60%) | 0.1–0.3 | **90–110** | ambient, chill-out, downtempo |
| Easy / Long run | Z2 (60–70%) | 0.4–0.6 | **120–130** | deep house, pop, podcast-friendly |
| Tempo / Threshold | Z3–Z4 (80–90%) | 0.6–0.8 | **130–150** | techno, drum & bass, steady rhythm |
| Intervals / HIIT | Z5 (90–100%) | 0.8–1.0 | **150+** | hard techno, metal, dubstep |

**The BPM–cadence ratio (key point, see `ontology_logic.md` §4.2).** The low
recovery band (90–110) is not a contradiction: at low intensity the foot
entrains in **half-time** (one step every two beats) and the goal is *calm*
(low arousal), while at high intensity the track is a **1:1 metronome** driving
cadence. So we optimize arousal at the bottom and synchronization at the top.

**Honesty note.** Practitioner BPM guides broadly agree (<120 warm-up/cool-down,
120–140 cruising, 140–160+ HIIT). The chapter's tempo-*preference* evidence
(Karageorghis) centres on 80–140 bpm with a ceiling above ~80% maxHRR; the
higher synchronization targets rest on the cadence-entrainment literature
(Van Dyck et al. 2015). We keep the two rationales separate rather than
overclaiming, and cite practitioner guides only as corroboration.

## 4. Cardiac benchmarks — where to hold back vs. push harder

The zones and the "safe max" come from standard exercise-physiology models:

| Reference model | Formula / rule | Use in AlgoRun |
|---|---|---|
| **HRmax — Fox et al. (1971)** | 220 − age | quick HRmax estimate |
| **HRmax — Tanaka et al. (2001)** | 208 − 0.7·age | more accurate HRmax (`maxHeartRateBpm`) |
| **Karvonen HR reserve (1957)** | target = rest + %·(HRmax − rest) | zone boundaries from resting + max HR |
| **5-zone model** | Z1 50–60%, Z2 60–70%, Z3 70–80%, Z4 80–90%, Z5 90–100% of HRmax | `IntensityZone` Z1–Z5 |

**Where to PUSH harder (energetic targets allowed):** Z3–Z5, i.e. up to ~90%
HRmax, where the evidence supports fast/high-energy music and cadence
entrainment (peak target 170–180 bpm, energy → 1.0).

**Where to HOLD BACK (force relaxing targets):** at/above the runner's
`safeMaxHeartRateBpm` (default: 90% HRmax, i.e. the Z4/Z5 boundary), the SHACL
`CriticalHeartRateShape` rejects any target > 140 bpm — slow music speeds HR
and lactate recovery (Szmedra & Bacharach 1998, cited in the chapter).

## 5. Injury-prevention benchmark (cadence)

- **Heiderscheit et al. (2011)**, *Effects of step rate manipulation on joint
  mechanics during running* (Med. Sci. Sports Exerc.): increasing step rate
  ~5–10% reduces joint loading and overstriding; large abrupt increases add
  injury risk. → SHACL `CadenceStepShape`: applied target BPM ≤ 1.05 × current
  cadence (never jump 140 spm → 180 bpm).

## 6. Control-system rules (implemented in the M5 Python server, not the KG)

The ontology decides *what* target and *how urgent*; the server decides *when*
to act, to avoid "schizophrenic" changes:

- **Hysteresis (smoothing):** decisions use a 1–2 min moving average of HR, not
  the instantaneous value; a 10 s spike is ignored.
- **Playback lock (cooldown):** when a track starts, a 2–3 min lock blocks
  song-change commands so the track can develop.
- **Panic button (immediate skip):** when the ontology sets
  `hasActionPriority EmergencyPriority` (HR ≥ safe max), the controller
  **bypasses the lock** and calls `sp.next_track()` for a hard cut. The SHACL
  `EmergencyTargetShape` guarantees the emergency target is calming (≤ 140 bpm).

### Panic-button threshold (decided)
**EmergencyPriority fires when the smoothed HR ≥ 93% HRmax OR ≥
safeMaxHeartRateBpm**, whichever is lower. 93% HRmax sits just below the top of
the Z5 training band, so hard intervals still run normally while a genuine
overshoot triggers the immediate skip. `safeMaxHeartRateBpm` defaults to 93%
HRmax and can be overridden per runner (e.g. a clinician-set absolute value).

## References

- Terry, P. C. & Karageorghis, C. I. (2011). *Chariots of Fire: The Role of
  Music in Sport and Exercise.*
- Karageorghis, C. I. & Terry, P. C. (2009). *The psychological, psychophysical
  and ergogenic effects of music in sport.*
- Van Dyck, E. et al. (2015). *Spontaneous Entrainment of Running Cadence to
  Music Tempo.* Sports Medicine-Open.
- Heiderscheit, B. C. et al. (2011). *Effects of step rate manipulation on
  joint mechanics during running.* Med. Sci. Sports Exerc.
- Tanaka, H., Monahan, K. D., Seals, D. R. (2001). *Age-predicted maximal
  heart rate revisited.* J. Am. Coll. Cardiol.
- Karvonen, M. J., Kentala, E., Mustala, O. (1957). *The effects of training on
  heart rate.* Ann. Med. Exp. Biol. Fenn.
- Szmedra, L. & Bacharach, D. W. (1998). *Effect of music on perceived exertion,
  heart rate, blood pressure and lactate.* Int. J. Sports Med.

Google Scholar entry point for further sources: search
*"Training Intensity Zones Music Synchronization"*. Practitioner corroboration:
Runlovers (2025/2026), RunDida, Runo, Runners Need BPM guides.
