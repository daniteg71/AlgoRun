"""Il validator supervisionato (M4): un Transformer come "logic gate" VALID/INVALID.

Architettura Generator/Validator del corso (la "architectural shift"):
  - il GENERATORE (`refinery.extract_candidates`) sovra-genera: tutte le
    coppie di entità compatibili con domain/range, senza trigger — su train
    ~1 positivo ogni 4 negativi, ceiling recall 0.39 (vs 0.14 baseline);
  - il VALIDATOR (questo modulo) è un Transformer fine-tuned che riceve
    (frase, candidato verbalizzato) e risponde VALIDO/INVALIDO. Il modello
    non "inventa" relazioni: fa solo da cancello logico stabile sui candidati
    proposti — mai generatore, sempre giudice.

Confronto richiesto dalla Rule 4: baseline trigger+distanza (M3) vs più
architetture di validator (Rule 4 vuole "multiple Transformer
architectures"), P/R/F1 sul grafo, per tier, su test.jsonl (mai usato in
training: si allena su train.jsonl e si sceglie la soglia su val.jsonl).

Modulo di BENCHMARK (quarantena): torch/transformers sono opzionali
(requirements-bench.txt), NON servono al prodotto. Due architetture, stesso
codice, cambia solo il nome del modello:
  - "distilbert" (distilbert-base-uncased) — leggero, veloce;
  - "roberta"    (roberta-base)            — più pesante, più accurato.

Uso:
  python -m benchmarks.validator train --arch distilbert   # fine-tuning (~2 min su MPS)
  python -m benchmarks.validator train --arch roberta
  python -m benchmarks.validator eval                       # confronto: baseline + ogni arch allenata
Ogni modello finisce in models/validator-<arch>/ (fuori da git).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from torch.utils.data import DataLoader, Dataset

from algorun.exam.nlp import dictionary_extract
from algorun.exam.refinery import (_gold_triples, _prf1, evaluate_on_dataset,
                              extract_candidates)

# architettura -> checkpoint HuggingFace. Aggiungerne una è una riga sola.
ARCHITECTURES = {
    "distilbert": "distilbert-base-uncased",
    "roberta": "roberta-base",
}
MODELS_ROOT = Path("models")
# sceglie l'acceleratore disponibile: GPU NVIDIA (cuda, es. Colab) ->
# GPU Apple Silicon (mps, es. MacBook M2) -> altrimenti CPU
if torch.cuda.is_available():
    DEVICE = "cuda"
elif torch.backends.mps.is_available():
    DEVICE = "mps"
else:
    DEVICE = "cpu"


def _model_dir(arch: str) -> Path:
    return MODELS_ROOT / f"validator-{arch}"


# ------------------------------------------------------------ verbalizzazione

def _readable(key) -> str:
    """Nome leggibile di un endpoint: 'the session' per il nodo canonico,
    altrimenti il local name dell'IRI (es. ...#WarmUp -> 'WarmUp')."""
    if isinstance(key, tuple):          # nodo canonico ("CANONICAL", tipo)
        return "the session"
    return key.split("#")[-1]


def verbalize(candidate: tuple) -> str:
    """(sogg, predicato, ogg) -> frase-ipotesi per il modello.
    Es.: ('...#WarmUp', '...#targetsEffort', '...#HighEffort')
      -> 'WarmUp targetsEffort HighEffort'."""
    subj, pred, obj = candidate
    return f"{_readable(subj)} {pred.split('#')[-1]} {_readable(obj)}"


# ------------------------------------------------------------ dati di training

def build_examples(path: Path | str, limit: int | None = None) -> list[dict]:
    """Da un JSONL annotato -> esempi (testo, ipotesi, etichetta 0/1).

    L'etichetta è 1 se il candidato compare fra le triple gold del record
    (con la stessa canonicalizzazione usata in refinery), 0 altrimenti.
    Le entità si estraggono col NER baseline — le stesse condizioni che il
    validator vedrà in inferenza (niente informazioni dal gold).
    """
    records = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
    if limit is not None:
        records = records[:limit]

    examples = []
    for rec in records:
        gold = _gold_triples(rec)
        for cand in extract_candidates(rec["text"], dictionary_extract(rec["text"])):
            examples.append({"text": rec["text"], "hypothesis": verbalize(cand),
                             "label": 1 if cand in gold else 0})
    return examples


class _PairDataset(Dataset):
    """Coppie (frase, ipotesi) tokenizzate per DistilBERT."""

    def __init__(self, examples: list[dict], tokenizer):
        enc = tokenizer([e["text"] for e in examples],
                        [e["hypothesis"] for e in examples],
                        truncation=True, padding=True, max_length=128,
                        return_tensors="pt")
        self.input_ids = enc["input_ids"]
        self.attention_mask = enc["attention_mask"]
        self.labels = torch.tensor([e["label"] for e in examples])

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, i):
        return {"input_ids": self.input_ids[i],
                "attention_mask": self.attention_mask[i],
                "labels": self.labels[i]}


# ------------------------------------------------------------------- training

def train_validator(arch: str = "distilbert",
                    train_path="data/synthetic/train.jsonl",
                    val_path="data/synthetic/val.jsonl",
                    out_dir: Path | str | None = None,
                    epochs: int = 3, batch_size: int = 16, lr: float = 5e-5):
    """Fine-tuning di un Transformer (`arch`) come classificatore binario
    VALID/INVALID. Stesso loop per qualunque architettura del registro —
    simmetria richiesta dalla Rule 7 (backend intercambiabili, stessa forma).

    Loop di training esplicito (niente Trainer) — più leggibile e senza
    dipendenze extra. Su Apple Silicon usa la GPU (MPS).
    """
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    model_name = ARCHITECTURES[arch]
    out_dir = Path(out_dir) if out_dir is not None else _model_dir(arch)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name, num_labels=2).to(DEVICE)

    train_ex = build_examples(train_path)
    val_ex = build_examples(val_path)
    print(f"train: {len(train_ex)} esempi "
          f"({sum(e['label'] for e in train_ex)} positivi) | val: {len(val_ex)}")

    loader = DataLoader(_PairDataset(train_ex, tokenizer),
                        batch_size=batch_size, shuffle=True)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)

    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        for batch in loader:
            batch = {k: v.to(DEVICE) for k, v in batch.items()}
            out = model(**batch)
            out.loss.backward()
            optimizer.step()
            optimizer.zero_grad()
            total_loss += out.loss.item()
        acc = _accuracy(model, tokenizer, val_ex)
        print(f"epoch {epoch + 1}/{epochs}  loss={total_loss / len(loader):.4f}  "
              f"val_accuracy={acc:.3f}")

    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)
    print(f"modello salvato in {out_dir}")


@torch.no_grad()
def _accuracy(model, tokenizer, examples: list[dict]) -> float:
    model.eval()
    loader = DataLoader(_PairDataset(examples, tokenizer), batch_size=64)
    correct = 0
    for batch in loader:
        batch = {k: v.to(DEVICE) for k, v in batch.items()}
        preds = model(**batch).logits.argmax(dim=-1)
        correct += (preds == batch["labels"]).sum().item()
    return correct / len(examples)


# ------------------------------------------------------------------ inferenza

_LOADED: dict[str, tuple] = {}   # model_dir -> (model, tokenizer), cache pigra


def _load(model_dir: Path | str):
    key = str(model_dir)
    if key not in _LOADED:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        tok = AutoTokenizer.from_pretrained(model_dir)
        model = AutoModelForSequenceClassification.from_pretrained(model_dir).to(DEVICE)
        model.eval()
        _LOADED[key] = (model, tok)
    return _LOADED[key]


@torch.no_grad()
def validated_triples(text: str, model_dir: Path | str) -> set[tuple]:
    """Il grafo predetto della pipeline avanzata: generatore pairwise ->
    validator DistilBERT -> restano solo i candidati giudicati VALIDI."""
    cands = extract_candidates(text, dictionary_extract(text))
    if not cands:
        return set()
    model, tok = _load(model_dir)
    enc = tok([text] * len(cands), [verbalize(c) for c in cands],
              truncation=True, padding=True, max_length=128,
              return_tensors="pt").to(DEVICE)
    keep = model(**enc).logits.argmax(dim=-1).tolist()
    return {c for c, k in zip(cands, keep) if k == 1}


def evaluate_with_validator(model_dir: Path | str,
                            path="data/synthetic/test.jsonl") -> dict:
    """P/R/F1 (complessivo + per tier) della pipeline generatore+validator,
    stessa metrica di refinery.evaluate_on_dataset per il confronto Rule 4."""
    records = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
    buckets: dict[str, list[int]] = {}

    def add(key, gold, pred):
        tp, fp, fn = buckets.setdefault(key, [0, 0, 0])
        buckets[key] = [tp + len(pred & gold), fp + len(pred - gold), fn + len(gold - pred)]

    for rec in records:
        gold = _gold_triples(rec)
        pred = validated_triples(rec["text"], model_dir)
        add("overall", gold, pred)
        add(f"tier:{rec['tier']}", gold, pred)

    result = {"overall": _prf1(*buckets.pop("overall"))}
    result["per_tier"] = {k.split(":", 1)[1]: _prf1(*v) for k, v in buckets.items()}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["train", "eval"])
    parser.add_argument("--arch", choices=list(ARCHITECTURES), default="distilbert",
                        help="solo per 'train': quale architettura allenare")
    args = parser.parse_args()

    if args.command == "train":
        train_validator(arch=args.arch)
        return

    print("== Baseline M3 (trigger+distanza) su test.jsonl ==")
    base = evaluate_on_dataset("data/synthetic/test.jsonl")
    print(f"  overall {base['overall']}")

    trained = [a for a in ARCHITECTURES if _model_dir(a).exists()]
    if not trained:
        print("\nNessun validator allenato — esegui prima 'train --arch <nome>'.")
        return

    results = {}
    for arch in trained:
        print(f"\n== M4 (pairwise + validator {arch}) su test.jsonl ==")
        adv = evaluate_with_validator(_model_dir(arch))
        results[arch] = adv
        print(f"  overall {adv['overall']}")

    header = f"\n{'tier':15}{'baseline':>12}" + "".join(f"{a:>14}" for a in trained)
    print(header)
    for tier, b in base["per_tier"].items():
        row = f"{tier:15}{b['f1']:>12.2f}"
        for arch in trained:
            row += f"{results[arch]['per_tier'][tier]['f1']:>14.2f}"
        print(row)


if __name__ == "__main__":
    main()
