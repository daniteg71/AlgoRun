# test del validator M4 (generatore pairwise + DistilBERT).
# il training NON gira nella suite (troppo lento): i test sull'inferenza
# si saltano se il modello non è ancora stato allenato
# (python -m algorun.validator train).

from pathlib import Path

import pytest

from algorun.nlp import dictionary_extract
from algorun.refinery import extract_candidates
from algorun.validator import MODEL_DIR, build_examples, verbalize
from algorun.ontology.loader import AR

_model_missing = not Path(MODEL_DIR).exists()


def test_pairwise_generator_overgenerates():
    # frase con 2 fasi + 1 effort: il pairwise deve proporre anche coppie
    # sbagliate (è il suo compito: dare al validator qualcosa da scartare)
    text = "The warmup phase targets higheffort, then the hard phase."
    cands = extract_candidates(text, dictionary_extract(text))
    assert (str(AR.WarmUp), str(AR.targetsEffort), str(AR.HighEffort)) in cands
    assert (str(AR.Hard), str(AR.targetsEffort), str(AR.HighEffort)) in cands  # negativo utile
    assert len(cands) >= 4


def test_verbalize():
    cand = (str(AR.WarmUp), str(AR.targetsEffort), str(AR.HighEffort))
    assert verbalize(cand) == "WarmUp targetsEffort HighEffort"
    canonical = (("CANONICAL", str(AR.WorkoutSession)), str(AR.hasPhase), str(AR.Hard))
    assert verbalize(canonical) == "the session hasPhase Hard"


def test_build_examples_has_both_labels():
    examples = build_examples("data/synthetic/val.jsonl", limit=20)
    labels = {e["label"] for e in examples}
    assert labels == {0, 1}      # senza negativi il validator non impara nulla


@pytest.mark.skipif(_model_missing, reason="modello non ancora allenato")
def test_validator_keeps_true_and_drops_false():
    from algorun.validator import validated_triples
    text = "The warmup phase targets higheffort."
    kept = validated_triples(text)
    assert (str(AR.WarmUp), str(AR.targetsEffort), str(AR.HighEffort)) in kept
    # il pairwise propone anche l'inverso sbagliato (Hard/…): non deve restare
    for triple in kept:
        assert triple[0] != triple[2]
