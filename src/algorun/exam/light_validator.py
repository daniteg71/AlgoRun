# =============================================================================
# COSA FA QUESTO FILE
# -----------------------------------------------------------------------------
# Un validator LEGGERO che fa lo stesso lavoro del Transformer (validator.py)
# ma con un modello classico: una REGRESSIONE LOGISTICA di scikit-learn su
# poche feature calcolate a mano. Niente rete neurale, niente torch, niente
# GPU: si allena in meno di un secondo su CPU e pesa pochi KB.
#
# Perché esiste: è la dimostrazione (e la scelta di ingegneria onesta) che per
# un problema semplice e già vincolato dallo schema dell'ontologia NON serve un
# modello enorme. È il terzo termine di paragone del benchmark del corso:
#     baseline simbolico  ->  modello classico (questo)  ->  Transformer
#
# Come funziona:
#   1. il GENERATORE (refinery.extract_candidates) propone tutte le coppie
#      compatibili con domain/range — le stesse che vede il Transformer;
#   2. per ogni coppia si calcolano poche FEATURE interpretabili (che relazione
#      è, il trigger è presente?, quanto è vicino alle entità, ...);
#   3. una regressione logistica dice VALIDO/INVALIDO. Con class_weight
#      "balanced" gestisce da sola lo sbilanciamento (19% positivi) — proprio
#      il problema che ha fatto collassare RoBERTa.
#
# Uso:  python -m algorun.light_validator   # allena e stampa il confronto
# =============================================================================

from __future__ import annotations

import json
from pathlib import Path

from algorun.exam.nlp import dictionary_extract
from algorun.ontology.loader import AR, load_ontology
from algorun.exam.refinery import (DISTANCE_WINDOW, _char_to_token_index, _gold_triples,
                              _lemma_of_word, _prf1, _trigger_occurrences,
                              evaluate_on_dataset, extract_candidates, tokenize)


# ------------------------------------------------------------------- feature

def _entity_token_positions(text: str, entities: list[dict]) -> dict[str, int]:
    """Per ogni entità NOMINATA nel testo, l'indice del token in cui inizia.
    Serve a misurare le distanze (le entità implicite/canoniche non ci sono)."""
    doc = tokenize(text)
    return {e["iri"]: _char_to_token_index(doc, e["start"]) for e in entities}


def _trigger_positions(text: str, prop_iri) -> list[int]:
    """Le posizioni (in token) in cui compare il trigger di una relazione."""
    schema = load_ontology()
    spec = schema.object_properties[prop_iri]
    lemmas = [t.lemma_.lower() for t in tokenize(text)]
    positions: list[int] = []
    for surface in spec.surface_forms:
        words = [_lemma_of_word(w) for w in surface.split()]
        positions.extend(_trigger_occurrences(lemmas, words))
    return positions


def features(text: str, candidate: tuple, ent_pos: dict[str, int]) -> dict:
    """Trasforma un candidato (sogg, predicato, ogg) in un dizionario di
    feature comprensibili. Sono queste che il modello impara a pesare."""
    subj, pred, obj = candidate
    prop_iri = AR.term(pred.split("#")[-1])
    triggers = _trigger_positions(text, prop_iri)

    # posizione degli endpoint (None se è il nodo canonico "la sessione")
    subj_pos = ent_pos.get(subj) if isinstance(subj, str) else None
    obj_pos = ent_pos.get(obj) if isinstance(obj, str) else None

    def nearest_trigger(pos):
        # distanza minima fra un endpoint e un trigger della relazione
        if pos is None or not triggers:
            return DISTANCE_WINDOW + 1        # "lontano/assente" = valore alto
        return min(abs(pos - t) for t in triggers)

    return {
        # QUALE relazione è: segnale forte (alcune sono quasi sempre valide)
        "predicate": pred.split("#")[-1],
        # il trigger della relazione compare nel testo?
        "trigger_present": bool(triggers),
        # quanto è vicino il trigger al soggetto / all'oggetto
        "dist_trigger_subj": nearest_trigger(subj_pos),
        "dist_trigger_obj": nearest_trigger(obj_pos),
        # distanza soggetto-oggetto (o valore alto se un endpoint è canonico)
        "dist_subj_obj": (abs(subj_pos - obj_pos)
                          if subj_pos is not None and obj_pos is not None
                          else DISTANCE_WINDOW + 1),
        # endpoint canonici (la sessione implicita) vs nominati nel testo
        "subj_canonical": not isinstance(subj, str),
        "obj_canonical": not isinstance(obj, str),
    }


# ---------------------------------------------------------- dati + addestramento

def _dataset(path: Path | str, limit: int | None = None):
    """Costruisce (lista di feature-dict, lista di etichette 0/1) da un JSONL.
    `limit` serve solo ai test, per non processare tutto il dataset."""
    records = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
    if limit is not None:
        records = records[:limit]
    X, y = [], []
    for rec in records:
        gold = _gold_triples(rec)
        entities = dictionary_extract(rec["text"])
        ent_pos = _entity_token_positions(rec["text"], entities)
        for cand in extract_candidates(rec["text"], entities):
            X.append(features(rec["text"], cand, ent_pos))
            y.append(1 if cand in gold else 0)
    return X, y


def train_light(train_path="data/synthetic/train.jsonl", limit: int | None = None):
    """Allena la regressione logistica. Ritorna (modello, vectorizer).

    DictVectorizer trasforma i dizionari di feature in vettori numerici
    (fa il one-hot delle feature categoriali come 'predicate' da solo).
    class_weight='balanced' compensa lo sbilanciamento 19/81.
    """
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.linear_model import LogisticRegression

    X, y = _dataset(train_path, limit)
    vectorizer = DictVectorizer(sparse=False)
    Xv = vectorizer.fit_transform(X)
    model = LogisticRegression(max_iter=1000, class_weight="balanced")
    model.fit(Xv, y)
    return model, vectorizer


# --------------------------------------------------------------- valutazione

def evaluate_light(train_path="data/synthetic/train.jsonl",
                   test_path="data/synthetic/test.jsonl",
                   train_limit: int | None = None,
                   test_limit: int | None = None) -> dict:
    """Allena su train, valuta su test: P/R/F1 sul grafo, complessivo e per
    tier — stessa metrica di refinery/validator per il confronto della Rule 4."""
    model, vectorizer = train_light(train_path, train_limit)
    records = [json.loads(l) for l in Path(test_path).read_text().splitlines() if l.strip()]
    if test_limit is not None:
        records = records[:test_limit]
    buckets: dict[str, list[int]] = {}

    def add(key, gold, pred):
        tp, fp, fn = buckets.setdefault(key, [0, 0, 0])
        buckets[key] = [tp + len(pred & gold), fp + len(pred - gold), fn + len(gold - pred)]

    for rec in records:
        gold = _gold_triples(rec)
        entities = dictionary_extract(rec["text"])
        ent_pos = _entity_token_positions(rec["text"], entities)
        cands = extract_candidates(rec["text"], entities)
        # predice VALIDO/INVALIDO per ogni candidato e tiene solo i validi
        pred = set()
        if cands:
            Xv = vectorizer.transform([features(rec["text"], c, ent_pos) for c in cands])
            for cand, keep in zip(cands, model.predict(Xv)):
                if keep == 1:
                    pred.add(cand)
        add("overall", gold, pred)
        add(f"tier:{rec['tier']}", gold, pred)

    result = {"overall": _prf1(*buckets.pop("overall"))}
    result["per_tier"] = {k.split(":", 1)[1]: _prf1(*v) for k, v in buckets.items()}
    return result


def main() -> None:
    print("== Baseline M3 (trigger+distanza) ==")
    base = evaluate_on_dataset("data/synthetic/test.jsonl")
    print(f"  overall {base['overall']}")
    print("\n== Validator LEGGERO (regressione logistica) ==")
    light = evaluate_light()
    print(f"  overall {light['overall']}")
    print("\n  per tier:")
    for tier, m in light["per_tier"].items():
        b = base["per_tier"][tier]
        print(f"    {tier:15} baseline F1={b['f1']:.2f} -> leggero F1={m['f1']:.2f}")


if __name__ == "__main__":
    main()
