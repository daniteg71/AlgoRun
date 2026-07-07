# PIPELINE.md — la logica completa (dal testo alla canzone)

```
              ┌──────────────────── INPUT UTENTE — frase ≤20 parole ─────────────────────┐
              │   "oggi 12 km/h per 40 min"     |     "oggi sono stanco, qualcosa chill"  │
              └────────────────────────────────────┬─────────────────────────────────────┘
                                                    ▼
                                   ESTRAZIONE FEATURE  (intent.py)
                     ┌──────────────────────────────┴──────────────────────────────┐
                     ▼                                                              ▼
              regex → NUMERI                                        SetFit → TIPO (5 classi)
         speed / pace / dist / durata                              detect_mood_seed → MOOD
                     │                                                              │
        ┌────────────┴────────────┐                                                │
        ▼ CI SONO NUMERI          ▼ NIENTE NUMERI                                   │
   REGIME QUANTITATIVO       REGIME QUALITATIVO                                     │
   bpm* = cadenza(velocità)  bpm* = centro banda tipo (AMPIA)                       │
   banda STRETTA (±3%)       focus MOOD + "non affaticare"                          │
   w_bpm ALTO (0.7–0.9)      w_bpm BASSO (0.2) · w_mood ALTO (0.8)                  │
   τ basso (precisione)      τ alto (varietà)                                       │
        └────────────┬────────────┘                                                ▼
                     ▼                                      MOOD → ONTOLOGIA GENERI (mood-oriented)
        TARGET INIZIALE {bpm*, energy*, W, τ} ◄──────────  seme = BUNCH di sottogeneri vicini al mood
                     │                                      d_genre = distanza sull'albero (Rada 1989)
 ════════════════════╪══════════════════ DURANTE LA CORSA (loop) ═══════════════════════════════════
                     ▼
        SENSORI ogni Δt (5–10 s)  →  sensor.py
        ┌────────────┬────────────┬────────────┐
        │   GPS      │  cadenza   │  BPM cuore  │
        │ → velocità │  → spm     │  → HRR      │
        └─────┬──────┴─────┬──────┴─────┬───────┘
              ▼            ▼             ▼
         v̄ (media)     c̄ (media)   HRR / effort / trend
              └────────────┴─────────────┘
                           ▼
              FUSIONE + CONTROLLO  (controller.adapt)  — media degli shot della canzone
              · cadenza reale c̄      → bpm* = c̄        (misura diretta, batte la formula)
              · velocità v̄ < richiesta → abbassa la banda (non ce la fa)
              · HRR ≥ 0.90            → SAFETY: forza recupero (ignora "spingi")
              · dici tempo ma HRR bassa → energia ↑ (motiva)
                           ▼
              SCORING  (scorer.py)  — per ogni canzone s
              Score(s) = w_bpm·d_bpm(s) + w_energy·d_energy(s) + w_genre·d_genre(s)
              d_bpm con correzione d'ottava (½×,1×,2×) ; d_genre dal seme-mood
                           ▼
              PROBABILITÀ  P(s) = softmax(−Score(s)/τ)
              τ alto (easy/fartlek) = esplora · τ→0 (tempo/interval) = sfrutta
                           ▼
              PROSSIMA CANZONE → play (Spotify)
                           │
              sliding window (no ripetizioni) ─────► (ricomincia al brano successivo)
```

---

## La matematica, scelta per scelta

### 1. Estrazione feature (`intent.py`)
- **Numeri** (regex): `speed_kmh` da "12 km/h", o da un passo "5:00 min/km" → `60 / (min + s/60)`.
- **Tipo** (SetFit, few-shot): 5 classi {easy, long, tempo, interval, fartlek}.
- **Mood** (keyword): parola di mood → genere-seme.

### 2. Il bivio: come si danno i pesi
**Se ci sono numeri → REGIME QUANTITATIVO** (c'è un bersaglio misurabile):
```
bpm* = clamp(134 + 2.9·velocità, 150, 190)        # cadenza; BPM = cadenza (Van Dyck 2015)
banda stretta: match se |bpm_s·m − bpm*|/bpm* ≤ 0.03,  m∈{½,1,2}
W = (w_bpm≈0.8, w_energy medio, w_genre basso) ;  τ basso
```
> Perché: se conosci la velocità, la **precisione biomeccanica del BPM domina** → peso alto al BPM, banda piccola.

**Se NON ci sono numeri → REGIME QUALITATIVO** (solo mood/sensazione):
```
bpm* = centro della banda del tipo (ampia) ;  energy* dal tipo
"non affaticare" → se easy/recovery, banda BASSA e cap sullo sforzo
W = (w_bpm≈0.2, w_mood/genere≈0.8) ;  τ alto
```
> Perché: nessun bersaglio numerico → si **ottimizza l'arousal** (mood + energia) e si **esplora** (Karageorghis & Terry 2009).

### 3. Il ruolo dell'ontologia (mood-oriented)
- L'ontologia mappa i **113 generi** in un albero `sottogenere → famiglia → super-famiglia`.
- Il **mood** estratto sceglie un **seme = bunch di sottogeneri** vicini (es. "carico" → metal / hardcore / hard-rock).
- `d_genre(s) = cammino_minimo(seme, genere_s)` normalizzato in [0,1] (**Rada et al. 1989**): vicino→0, lontano→1.
- Entra nello Score come `w_genre·d_genre`. Così **il mood pilota il genere**, e l'ontologia diventa un vero pezzo del recommender (non decorazione).

### 4. I dati dai sensori (GPS, cadenza, BPM) — come arrivano
Ogni `Δt` (5–10 s) durante una canzone arriva uno **shot**:
```
GPS          → velocità reale  v_t (km/h)
accelerometro→ cadenza reale   c_t (spm)
fascia cardio→ battito         HR_t (bpm cuore)
```
Aggregazione sulla canzone in corso (media o EWMA `S_t = α·X_t + (1−α)·S_{t−1}`, **Roberts 1959**) → `v̄, c̄, HR̄`.
Dallo `HR̄`:
```
HRR = (HR̄ − HR_rest) / (HR_max − HR_rest)          # Karvonen 1957
HR_max = 208 − 0.7·età                              # Tanaka 2001
effort: Low<0.40 · Target<0.70 · High<0.85 · VeryHigh≥0.85
trend = pendenza della regressione dei BPM sul tempo
```

### 5. Fusione + controllo (come si aggiorna il target) — `controller.adapt`
```
cadenza reale c̄       → bpm* = c̄           # misura diretta > formula da velocità
velocità v̄ < richiesta → banda ↓            # "non raggiungi il ritmo" -> abbassa
HRR ≥ 0.90            → SAFETY: recupero    # cuore a mille: IGNORA l'intento "spingi"
tipo=tempo & HRR bassa → energia ↑          # dici tempo ma vai piano -> ti carico
tipo=fartlek          → segui: HRR↑→su, HRR↓→chill
```
È qui che **input dell'utente (target iniziale)** e **sensori (aggiustamento continuo)** si fondono; il cuore ha l'ultima parola (safety).

### 6. Scoring → probabilità (`scorer.py`)
```
d_bpm(s)   = min_{m∈{½,1,2}} |bpm_s·m − bpm*| / bpm*     # correzione d'ottava (Van Dyck)
Score(s)   = w_bpm·d_bpm + w_energy·|energy_s−energy*| + w_genre·d_genre(s)
P(s)       = softmax(−Score(s)/τ) = e^{−Score/τ} / Σ e^{−Score/τ}    # Sutton & Barto
scelta     = campiona da P (τ alto = esplora)  |  argmin Score (τ→0 = sfrutta)
```
La **sliding window** esclude le ultime N canzoni (no ripetizioni / no salti bruschi).

### 7. Perché è una buona soluzione per il corso
- **Copre tutti gli utenti** con UN solo sistema: chi dà numeri (quantitativo) e chi dà solo il mood (qualitativo) → un bivio, stessa pipeline.
- **Densa di teoria citabile**: Van Dyck, Karvonen, Tanaka, Roberts, Rada, Russell, Karageorghis, Sutton & Barto → rigore per il Paper (vedi `THEORY.md`).
- **Neuro-simbolica / novità**: l'ontologia dei generi (mood-oriented) *guida* il modello vettoriale — grafo simbolico + scoring ML.
- **Ciberfisica / ambizione tecnica**: l'anello sensori (GPS+cadenza+HR) → adattamento in tempo reale + safety.
- **Benchmarkabile**: regole vs SetFit (intento), soglie vs distanza pesata (scelta), ablation su pesi/τ/soglie.
- **Onesta**: bande/pesi/τ/soglie sono **design → ablation**, non citazioni finte.

*(Nota: il dataset sensori attuale `physiological_windows.csv` ha solo l'HR; GPS e cadenza sono nel modello ma le colonne relative vanno aggiunte per attivare il feedback di velocità/cadenza.)*
