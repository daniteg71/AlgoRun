"""Il validator supervisionato (M4): DistilBERT come "logic gate" VALID/INVALID.

Architettura Generator/Validator del corso (la "architectural shift"):
  - il GENERATORE (`refinery.extract_candidates`) sovra-genera: tutte le
    coppie di entità compatibili con domain/range, senza trigger — su train
    ~1 positivo ogni 4 negativi, ceiling recall 0.39 (vs 0.14 baseline);
  - il VALIDATOR (questo modulo) è un DistilBERT fine-tuned che riceve
    (frase, candidato verbalizzato) e risponde VALIDO/INVALIDO. Il modello
    non "inventa" relazioni: fa solo da cancello logico stabile sui candidati
    proposti — mai generatore, sempre giudice.

Confronto richiesto dalla Rule 4: baseline trigger+distanza (M3) vs questo
generatore+validator, P/R/F1 sul grafo, per tier, su test.jsonl (mai usato
in training: si allena su train.jsonl e si sceglie la soglia su val.jsonl).

Uso:
  python -m algorun.validator train        # fine-tuning (~2 min su MPS)
  python -m algorun.validator eval         # confronto su test.jsonl
Il modello finisce in models/validator-distilbert/ (fuori da git).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from torch.utils.data import DataLoader, Dataset

from algorun.nlp import dictionary_extract
from algorun.refinery import (_gold_triples, _prf1, evaluate_on_dataset,
                              extract_candidates)

MODEL_NAME = "distilbert-base-uncased"
MODEL_DIR = Path("models/validator-distilbert")
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"


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

def train_validator(train_path="data/synthetic/train.jsonl",
                    val_path="data/synthetic/val.jsonl",
                    out_dir: Path | str = MODEL_DIR,
                    epochs: int = 3, batch_size: int = 16, lr: float = 5e-5):
    """Fine-tuning di DistilBERT come classificatore binario VALID/INVALID.

    Loop di training esplicito (niente Trainer) — più leggibile e senza
    dipendenze extra. Su Apple Silicon usa la GPU (MPS).
    """
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=2).to(DEVICE)

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

    out_dir = Path(out_dir)
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

_LOADED = None   # (model, tokenizer), caricati pigramente una sola volta


def _load(model_dir: Path | str = MODEL_DIR):
    global _LOADED
    if _LOADED is None:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        tok = AutoTokenizer.from_pretrained(model_dir)
        model = AutoModelForSequenceClassification.from_pretrained(model_dir).to(DEVICE)
        model.eval()
        _LOADED = (model, tok)
    return _LOADED


@torch.no_grad()
def validated_triples(text: str, model_dir: Path | str = MODEL_DIR) -> set[tuple]:
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


def evaluate_with_validator(path="data/synthetic/test.jsonl",
                            model_dir: Path | str = MODEL_DIR) -> dict:
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
    args = parser.parse_args()

    if args.command == "train":
        train_validator()
        return

    print("== Baseline M3 (trigger+distanza) su test.jsonl ==")
    base = evaluate_on_dataset("data/synthetic/test.jsonl")
    print(f"  overall {base['overall']}")
    print("\n== M4 (pairwise + validator DistilBERT) su test.jsonl ==")
    adv = evaluate_with_validator()
    print(f"  overall {adv['overall']}")
    print("\n  per tier:")
    for tier, m in adv["per_tier"].items():
        b = base["per_tier"][tier]
        print(f"    {tier:15} baseline F1={b['f1']:.2f} -> validator F1={m['f1']:.2f}")


if __name__ == "__main__":
    main()
