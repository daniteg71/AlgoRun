# STUDY_MAP.md — cosa devo studiare

Repo diviso in **3 blocchi** per capire cosa spiegare all'esame.

## 🎯 IL PRODOTTO — il funzionamento finale (STUDIA E SPIEGA QUESTO)
`src/algorun/` (i file in cima) + i dati. Flusso completo in `docs/PIPELINE.md`.

| File | Cosa fa | Teoria |
|---|---|---|
| `intent.py` | frase → tipo di corsa (SetFit) + numeri (regex) + mood → `params` | Van Dyck (cadenza→BPM), Russell (mood) |
| `sensor.py` | finestra di BPM cardiaci → HRR / sforzo / trend | Karvonen, Tanaka, Roberts (EWMA) |
| `scorer.py` | distanza pesata al target + softmax → probabilità → canzone | Sutton & Barto (softmax), ottava (Van Dyck) |
| `controller.py` | **l'anello**: sensori → aggiorna il target (per tipo) + safety → prossima canzone | fusione + controllo |
| `genre_graph.py` | distanza tra generi sull'albero (ontologia **mood-oriented**) | Rada 1989 (shortest path) |
| `ontology/genres.ttl` | l'albero dei 113 generi | — |
| `data/music/songs.csv` · `data/processed/physiological_windows.csv` | catalogo + dati sensore | — |

Teoria completa: **`docs/PIPELINE.md`** (grafico + matematica) e **`docs/THEORY.md`** (formule → fonti).

## 📚 BINARIO ESAME — testo → Knowledge Graph (Block 14), separato in `src/algorun/exam/`
Il pezzo "ontologia + refinery + benchmark" richiesto dalla traccia. **Il prodotto NON lo usa.**

| File | Cosa fa |
|---|---|
| `exam/nlp.py` | NER a dizionario (label OWL) |
| `exam/refinery.py` | testo → triple candidate |
| `exam/shacl_gate.py` | gate SHACL (domain/range) |
| `exam/light_validator.py` | validator leggero (champion del benchmark, F1 0.43) |
| `exam/datagen/` | generatore del dataset sintetico tiered |
| `ontology/algorun.owl` · `shapes.ttl` | ontologia di dominio + vincoli |
| `ontology/evaluation.py` | competency questions |
| `benchmarks/validator.py` | DistilBERT (benchmark, torch opzionale) |

## 🔧 SUPPORTO — non è "funzionamento", non da spiegare come tale
- `tests/` — test automatici
- `training/train_intent.py` — allena SetFit (`python training/train_intent.py`)
- `docs/` — PIPELINE.md, THEORY.md
- `ARCHITECTURE.md`, `README.md`, `GUIDELINES.md`, `CLAUDE.md`, `ALGORITHMS.md`, `collab/` — documenti di progetto
- `pyproject.toml`, `requirements*.txt` — configurazione

---
**In una riga:** studia `src/algorun/` (i 5 file del prodotto) + `docs/PIPELINE.md`. Il resto è esame (`exam/`) o supporto.
