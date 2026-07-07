# THEORY.md — Fondamenti teorici e citazioni

Ogni formula usata nel progetto, con la sua **fonte**. Serve a spiegare le scelte
nel Paper (Related Work + Methodology + References). Regola: ciò che ha una fonte
si cita; ciò che è **scelta di design** si dichiara come tale e si giustifica con
un'**ablation** — mai citazioni finte.

Legenda: ✅ = fonte citabile · ⚙️ = design (→ ablation).

---

## Parte A — Il prodotto (recommendation system)

### A1. Velocità → cadenza → BPM desiderato   `intent.bpm_from_speed`
```
cadenza(spm) = clamp(134 + 2.9 · velocità(km/h), 150, 190)
BPM_target   = cadenza            (entrainment 1:1; anche ½× e 2×)
```
- ✅ **Van Dyck et al. 2015** (*Sports Medicine – Open*): i corridori sincronizzano
  spontaneamente il passo al beat; cadenza naturale ~150–200 spm.
- ✅ **Van Dyck & Moens et al. 2018** (*PLOS ONE*): l'entrainment tiene entro **±2.5–3%**;
  un lieve bias tempo-avanti aumenta la motivazione.
- ⚙️ coefficienti `134 / 2.9` = regressione calibrata (la cadenza cresce ~linearmente
  con la velocità); il clamp 150–190 dai range naturali.

### A2. Sforzo dal cuore (HRR) e zone   `sensor.compute_hrr / classify_effort`
```
HRR = (HR − HR_rest) / (HR_max − HR_rest)                 # Karvonen
HR_max = 208 − 0.7·età   (oppure 220 − età)
zone:  HRR<0.40 Low · <0.70 Target · <0.85 High · ≥0.85 VeryHigh
```
- ✅ **Karvonen, Kentala & Mustala 1957** — Heart Rate Reserve.
- ✅ **Tanaka et al. 2001** — HR_max = 208 − 0.7·età; **Fox et al. 1971** — 220 − età.
- ⚙️ soglie 0.40/0.70/0.85 = zone d'allenamento standard (design).

### A3. Smoothing dei sensori (EWMA)   *(per il feedback live)*
```
S_t = α·X_t + (1−α)·S_{t−1}          α ≈ 0.3     # memoria O(1)
```
- ✅ **Roberts 1959** — Exponentially Weighted Moving Average (controllo di processo).

### A4. Trend del cuore   `sensor.classify_trend`
```
pendenza = regressione lineare dei BPM sul tempo
> +0.05 bpm/s → Increasing · < −0.05 → Decreasing · altrimenti Stable
```
- ⚙️ soglia 0.05 bpm/s (~3 bpm) = design.

### A5. Scelta della canzone: distanza pesata + softmax   `scorer`
```
d_bpm(s)   = min_{m∈{½,1,2}} |bpm_s·m − bpm*| / bpm*        # correzione d'ottava
Score(s)   = w_bpm·d_bpm + w_energy·|energy_s−energy*| + w_genre·d_genre(s)
P(s)       = softmax(−Score(s) / τ)                        # scelta
```
- ✅ correzione d'ottava (½×/1:1/2×) da **Van Dyck 2015** (half-time entrainment).
- ✅ **Sutton & Barto**, *Reinforcement Learning: An Introduction* — softmax/Boltzmann
  (e ε-greedy) per l'**exploration/exploitation**: τ alto esplora, τ→0 sfrutta.
- ⚙️ distanza euclidea pesata al target (riferimento d'ingegneria: pattern MaxHilsdorf);
  pesi `W` e τ per tipo = design.

### A6. Ontologia dei generi: distanza semantica   `genre_graph`
```
d_genre(a,b) = cammino_minimo(a,b) sull'albero skos:broader, normalizzato in [0,1]
```
- ✅ **Rada et al. 1989** — distanza semantica = shortest path su una rete di concetti.

### A7. Mood → genere-seme   `intent.detect_mood_seed`
- ✅ **Russell 1980** — modello circumplex (valenza × arousal): il mood si colloca in
  uno spazio 2D che orienta la scelta del genere.
- ✅ **Karageorghis & Terry 2009** — tempo/energia musicale ↔ arousal e resa sportiva.
- ⚙️ la tabella mood→genere e i pesi = design.

### A8. Fusione testo+sensore e Safety Override   `controller.adapt`
```
target iniziale (testo)  ⊕  aggiornamento (media shot HRR/effort)   # fusione a regole
if HRR ≥ 0.90:  forza recupero (bpm↓, energy↓)                       # safety override
```
- ⚙️ regola di fusione e soglia di sicurezza 0.90·(zona max) = design (ancorato al
  limite fisiologico max-HR). Il controllo proporzionale è teoria del controllo classica.

---

## Parte B — L'esame (Data Refinery: testo → Knowledge Graph)

### B1. Modelli
- ✅ **Vaswani et al. 2017** — Transformer (*Attention is all you need*).
- ✅ **Devlin et al. 2019** — BERT · **Sanh et al. 2019** — DistilBERT · **Liu et al. 2019** — RoBERTa.
- ✅ **Zaratiana et al. 2024** — GLiNER · **Chen et al. 2019** — JointBERT (contendenti).

### B2. Ontologia, vincoli e grafo
- ✅ **W3C OWL 2** (2012) · **RDF 1.1** (2014) · **SPARQL 1.1** (2013).
- ✅ **W3C SHACL** (2017) — constraint gate su domain/range (le triple valide entrano nel KG).

### B3. Architettura Generator→Validator
- Il modello **non genera** la relazione: sovra-genera candidati e un validator
  supervisionato fa da **cancello logico** VALID/INVALID (la "architectural shift"
  della traccia Block 14). Benchmark: baseline a regole vs Transformer, P/R/F1 per tier.

### B4. Librerie
- ✅ **spaCy** (Honnibal & Montani) · **scikit-learn** (Pedregosa et al. 2011) ·
  **HuggingFace Transformers** (Wolf et al. 2020) · **PyTorch** (Paszke et al. 2019) ·
  **RDFLib** · **pySHACL** · **NumPy** (Harris et al. 2020) · **pandas** · **RapidFuzz**.

---

## References (IEEE)

[1] E. Van Dyck et al., "Spontaneous entrainment of running cadence to music tempo," *Sports Medicine – Open*, 1:15, 2015.
[2] B. Moens, E. Van Dyck et al., "Optimizing beat-synchronized running to music," *PLOS ONE*, 13(12):e0208702, 2018.
[3] M. J. Karvonen, E. Kentala, O. Mustala, "The effects of training on heart rate," *Ann. Med. Exp. Biol. Fenn.*, 35(3):307–315, 1957.
[4] H. Tanaka, K. D. Monahan, D. R. Seals, "Age-predicted maximal heart rate revisited," *J. Am. Coll. Cardiol.*, 37(1):153–156, 2001.
[5] S. M. Fox, J. P. Naughton, W. L. Haskell, "Physical activity and the prevention of coronary heart disease," *Ann. Clin. Res.*, 3:404–432, 1971.
[6] S. W. Roberts, "Control chart tests based on geometric moving averages," *Technometrics*, 1(3):239–250, 1959.
[7] R. S. Sutton, A. G. Barto, *Reinforcement Learning: An Introduction*, MIT Press, 2018.
[8] R. Rada, H. Mili, E. Bicknell, M. Blettner, "Development and application of a metric on semantic nets," *IEEE Trans. Systems, Man, and Cybernetics*, 19(1):17–30, 1989.
[9] J. A. Russell, "A circumplex model of affect," *J. Personality and Social Psychology*, 39(6):1161–1178, 1980.
[10] C. I. Karageorghis, P. C. Terry, "The psychological, psychophysical and ergogenic effects of music in sport," in *Sport and Exercise Psychology*, 2009.
[11] A. Vaswani et al., "Attention is all you need," *NeurIPS*, 2017.
[12] J. Devlin et al., "BERT," *NAACL-HLT*, 2019.
[13] V. Sanh et al., "DistilBERT," arXiv:1910.01108, 2019.
[14] Y. Liu et al., "RoBERTa," arXiv:1907.11692, 2019.
[15] U. Zaratiana et al., "GLiNER," *NAACL*, 2024.
[16] Q. Chen et al., "BERT for joint intent classification and slot filling," arXiv:1902.10909, 2019.
[17] H. Knublauch, D. Kontokostas, "Shapes Constraint Language (SHACL)," *W3C Recommendation*, 2017.
[18] F. Pedregosa et al., "Scikit-learn," *JMLR*, 12:2825–2830, 2011.

*(BibTeX completo: vedi il dossier del Paper.)*
