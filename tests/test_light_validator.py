# test del validator LEGGERO (regressione logistica).
# usa subset piccoli (limit) perché il calcolo delle feature con spaCy su
# tutto il dataset è lento; qui verifichiamo solo che la catena funzioni e
# che il modello leggero batta il baseline simbolico.

from algorun.light_validator import (_entity_token_positions, evaluate_light,
                                     features)
from algorun.nlp import dictionary_extract
from algorun.ontology.loader import AR


def test_features_shape():
    text = "The warmup phase targets higheffort."
    ents = dictionary_extract(text)
    ent_pos = _entity_token_positions(text, ents)
    cand = (str(AR.WarmUp), str(AR.targetsEffort), str(AR.HighEffort))
    f = features(text, cand, ent_pos)
    # le feature chiave devono esserci
    assert f["predicate"] == "targetsEffort"
    assert f["trigger_present"] is True
    assert "dist_trigger_obj" in f and "dist_subj_obj" in f


def test_light_beats_baseline_on_subset():
    # allena su 120 record, valuta su 40: deve superare il baseline (F1 0.24)
    result = evaluate_light(train_limit=120, test_limit=40)
    assert result["overall"]["f1"] > 0.30
    # e non deve collassare a zero (il problema di RoBERTa mal tarata)
    assert result["overall"]["recall"] > 0.0
