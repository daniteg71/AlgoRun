"""M2 tests — synthetic dataset generation, annotation integrity, split."""

from algorun.datagen.generator import SPLIT_RATIOS, generate, split_records
from algorun.datagen.validate import validate_record
from algorun.ontology.loader import load_ontology


def test_split_ratios_are_70_15_15():
    """Rule 2: the split is non-negotiable."""
    assert SPLIT_RATIOS == (0.70, 0.15, 0.15)


def test_generation_is_deterministic():
    a = generate(per_tier=10, seed=42)
    b = generate(per_tier=10, seed=42)
    assert a == b


def test_all_four_tiers_generated():
    records = generate(per_tier=5)
    tiers = {rec["tier"] for rec in records}
    assert tiers == {"explicit", "implicit", "long_distance", "nested"}


def test_every_record_validates_against_ontology():
    ontology = load_ontology()
    records = generate(per_tier=25)
    for rec in records:
        errors = validate_record(rec, ontology)
        assert not errors, errors


def test_mentioned_entities_have_correct_spans():
    records = generate(per_tier=10)
    for rec in records:
        for ent in rec["entities"]:
            if ent["mentioned"]:
                assert ent["spans"], f"{rec['id']}: no span for {ent['surface']}"
                for start, end in ent["spans"]:
                    assert rec["text"][start:end].lower() == ent["surface"].lower()


def test_nested_tier_has_overlapping_triples():
    """Nested tier means multiple triples sharing entities in one text."""
    records = [r for r in generate(per_tier=10) if r["tier"] == "nested"]
    for rec in records:
        assert len(rec["triples"]) >= 4
        subjects = [t[0] for t in rec["triples"]]
        assert len(subjects) != len(set(subjects)) or len(rec["triples"]) > 4


def test_stratified_split_keeps_all_tiers_in_each_split():
    records = generate(per_tier=40)
    splits = split_records(records)
    for name, recs in splits.items():
        tiers = {rec["tier"] for rec in recs}
        assert tiers == {"explicit", "implicit", "long_distance", "nested"}, name
    total = sum(len(r) for r in splits.values())
    assert total == len(records)
    assert abs(len(splits["train"]) / total - 0.70) < 0.02
    assert abs(len(splits["val"]) / total - 0.15) < 0.02
    assert abs(len(splits["test"]) / total - 0.15) < 0.02
