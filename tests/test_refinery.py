# test del modulo di estrazione relazioni (M3, baseline trigger+distanza).
#
# i numeri qui sotto sono MISURATI, non aspirazionali: la baseline ha
# precisione altissima (il filtro domain/range scarta le coppie sbagliate)
# ma recall bassa, per due limiti reali e documentati in refinery.py:
#   - vocabolario chiuso (titoli canzoni/playlist/nomi non sono nell'ontologia)
#   - alcune relazioni (hasWorkoutType, hasEffortState) non hanno mai il loro
#     trigger letterale vicino all'entità nelle frasi del dataset

from algorun.exam.refinery import evaluate_on_dataset, extract_relations
from algorun.exam.nlp import dictionary_extract
from algorun.ontology.loader import AR


def _relations(text: str):
    return extract_relations(text, dictionary_extract(text))


def test_hasphase_recovered_with_intervening_words():
    # il trigger "includes phase" non è contiguo nel testo ("includes A HARD
    # phase") — il matching a finestra di token deve comunque trovarlo
    rels = _relations("The session includes a hard phase.")
    assert (("CANONICAL", str(AR.WorkoutSession)), str(AR.hasPhase), str(AR.Hard)) in rels


def test_targets_effort_recovered():
    rels = _relations("The warmup phase targets higheffort.")
    assert (str(AR.WarmUp), str(AR.targetsEffort), str(AR.HighEffort)) in rels


def test_domain_range_filter_rejects_incompatible_pair():
    # "suits" è il trigger di suitsPhase (Song->TrainingPhase), ma il titolo
    # della canzone non è un individuo dell'ontologia: nessuna coppia valida
    rels = _relations("The song Silver Lungs suits the steady phase.")
    assert rels == []


def test_evaluate_on_dataset_precision_is_high_recall_is_low():
    # limit=30 per velocità del test; i numeri sul dataset intero sono nel
    # demo CLI (python -m algorun.refinery)
    result = evaluate_on_dataset("data/synthetic/val.jsonl", limit=30)
    assert result["overall"]["precision"] >= 0.9   # il filtro domain/range funziona
    assert result["overall"]["recall"] < 0.5        # limite noto, non un bug


def test_perfectly_triggered_relations_have_full_recall():
    result = evaluate_on_dataset("data/synthetic/val.jsonl", limit=60)
    assert result["per_relation"]["hasPhase"]["recall"] >= 0.9
    assert result["per_relation"]["targetsEffort"]["recall"] >= 0.9


def test_out_of_vocabulary_relations_are_unrecoverable():
    # limite documentato: titoli/nomi liberi non sono nel dizionario
    result = evaluate_on_dataset("data/synthetic/val.jsonl", limit=60)
    assert result["per_relation"]["suitsPhase"]["recall"] == 0.0
    assert result["per_relation"]["hasGenre"]["recall"] == 0.0
