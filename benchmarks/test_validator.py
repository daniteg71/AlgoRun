# test del validator M4 (generatore pairwise + Transformer). il training NON
# gira nella suite (troppo lento): i test sull'inferenza si saltano per
# ogni architettura non ancora allenata (python -m algorun.validator train
# --arch distilbert|roberta).

import pytest

# torch/transformers sono opzionali (requirements-bench.txt): se assenti,
# l'intero benchmark si salta invece di far fallire la suite del core.
pytest.importorskip("torch")
pytest.importorskip("transformers")

from algorun.nlp import dictionary_extract
from algorun.refinery import extract_candidates
from algorun.ontology.loader import AR
from benchmarks.validator import ARCHITECTURES, _model_dir, build_examples, verbalize

_trained = [a for a in ARCHITECTURES if _model_dir(a).exists()]


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


@pytest.mark.skipif(not _trained, reason="nessuna architettura ancora allenata")
@pytest.mark.parametrize("arch", ARCHITECTURES)
def test_validator_keeps_true_and_drops_false(arch):
    from benchmarks.validator import validated_triples
    if arch not in _trained:
        pytest.skip(f"{arch} non ancora allenata")
    text = "The warmup phase targets higheffort."
    kept = validated_triples(text, _model_dir(arch))
    assert (str(AR.WarmUp), str(AR.targetsEffort), str(AR.HighEffort)) in kept
    # il pairwise propone anche l'inverso sbagliato (Hard/…): non deve restare
    for triple in kept:
        assert triple[0] != triple[2]
