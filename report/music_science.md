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

| State (zone) | BPM band | Energy | Duration | Genres |
|---|---|---|---|---|
| Warm-up / Recovery (Z1–Z2) | **120–140** | 0.2–0.5 | — | ambient, soft electronic, hypnotic |
| Tempo / Moderate (Z3) | **150–160** | 0.5–0.75 | ≥ 6 min (flow) | steady house, driving rock |
| Interval / Peak (Z4–Z5) | **170–180** | 0.75–1.0 | ≤ 4 min (bouts) | techno, drum & bass |

**Honesty note (important for the report).** The 120–140 band is directly
supported by Terry & Karageorghis as the core *motivational* range, and the
chapter warns that few tracks exist at very high tempi (ceiling above 80%
maxHRR). The **150–180** targets come instead from the **cadence-synchronization**
literature (Van Dyck et al. 2015; Karageorghis et al. beat-synchronized
running), where the target is footfall entrainment, not tempo preference. We
cite both and keep the two rationales separate rather than overclaiming.

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

### Open decision — the panic-button threshold
Proposed default: **EmergencyPriority fires when the smoothed HR ≥ 95% HRmax
OR ≥ safeMaxHeartRateBpm**, whichever the runner set. To be confirmed with the
teammate (see HANDOFF).

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
