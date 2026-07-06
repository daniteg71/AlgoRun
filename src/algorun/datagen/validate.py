# =============================================================================
# COSA FA QUESTO FILE
# -----------------------------------------------------------------------------
# Controlla che il dataset sintetico (i file train/val/test .jsonl) sia SANO,
# cioè rispetti la Rule 2 del corso. Per ogni record verifica:
#   - che abbia tutte le chiavi previste (id, tier, text, entities, triples);
#   - che gli span annotati ritaglino DAVVERO la parola dichiarata nel testo;
#   - che ogni entità/relazione esista nell'ontologia (grounding);
#   - che i 4 livelli di complessità ci siano tutti e che lo split sia 70/15/15.
#
# È una "rete di sicurezza": se generi il dataset e qui salta fuori un errore,
# vuol dire che qualcosa non torna fra i template e l'ontologia.
#
# Uso:  python -m algorun.datagen.validate --data data/synthetic
# =============================================================================

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from rdflib import URIRef

from algorun.ontology.loader import load_ontology

# chiavi obbligatorie in ogni record del dataset
REQUIRED_KEYS = {"id", "tier", "text", "entities", "triples"}
# i 4 livelli di complessità previsti
TIERS = {"explicit", "implicit", "long_distance", "nested"}
# proporzioni attese dello split e tolleranza ammessa (±2%)
EXPECTED_RATIOS = {"train": 0.70, "val": 0.15, "test": 0.15}
RATIO_TOLERANCE = 0.02


def load_split(path: Path) -> list[dict]:
    """Legge un file .jsonl (un record JSON per riga) in una lista di dict."""
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def validate_record(rec: dict, ontology) -> list[str]:
    """Controlla UN singolo record e ritorna la lista degli errori trovati
    (lista vuota = record perfetto)."""
    errors: list[str] = []

    # 1) tutte le chiavi devono esserci — se ne mancano, inutile continuare
    missing = REQUIRED_KEYS - rec.keys()
    if missing:
        return [f"{rec.get('id', '?')}: missing keys {missing}"]
    if rec["tier"] not in TIERS:
        errors.append(f"{rec['id']}: unknown tier {rec['tier']}")

    # 2) controllo delle entità: span corretti e tipo esistente nell'ontologia
    entity_ids = set()
    for ent in rec["entities"]:
        entity_ids.add(ent["id"])
        # se l'entità è "nominata" nel testo, ogni span deve ritagliare
        # esattamente la parola dichiarata (surface)
        if ent.get("mentioned"):
            for start, end in ent.get("spans", []):
                sliced = rec["text"][start:end].lower()
                if sliced != ent["surface"].lower():
                    errors.append(
                        f"{rec['id']}: span [{start},{end}] is {sliced!r}, "
                        f"expected {ent['surface']!r}")
        # il tipo dell'entità deve essere una classe vera dell'ontologia
        if URIRef(ent["type_iri"]) not in ontology.classes:
            errors.append(f"{rec['id']}: unknown type IRI {ent['type_iri']}")

    # 3) controllo delle triple: gli endpoint devono essere entità note e la
    #    relazione deve esistere nell'ontologia con domain/range dichiarati
    for subj, rel, obj in rec["triples"]:
        if subj not in entity_ids or obj not in entity_ids:
            errors.append(f"{rec['id']}: triple references unknown entity")
        spec = ontology.object_properties.get(URIRef(rel))
        if spec is None:
            errors.append(f"{rec['id']}: relation {rel} not in ontology")
        elif spec.domain is None or spec.range is None:
            errors.append(f"{rec['id']}: relation {rel} lacks domain/range")
    return errors


def validate_dataset(data_dir: Path) -> tuple[bool, str]:
    """Valida i tre split insieme: errori nei record + proporzioni + copertura
    dei 4 livelli. Ritorna (tutto_ok, report_testuale)."""
    ontology = load_ontology()
    splits = {name: load_split(data_dir / f"{name}.jsonl")
              for name in EXPECTED_RATIOS}
    total = sum(len(recs) for recs in splits.values())
    lines: list[str] = [f"total records: {total}"]
    ok = True

    for name, recs in splits.items():
        # raccoglie tutti gli errori di tutti i record di questo split
        errors = [e for rec in recs for e in validate_record(rec, ontology)]
        ratio = len(recs) / total if total else 0
        expected = EXPECTED_RATIOS[name]
        ratio_ok = abs(ratio - expected) <= RATIO_TOLERANCE
        tier_counts = Counter(rec["tier"] for rec in recs)
        lines.append(
            f"{name}: {len(recs)} records ({ratio:.1%}, expected {expected:.0%})"
            f" tiers={dict(tier_counts)}")
        # se qualcosa non va, marca il fallimento e stampa i primi 20 errori
        if errors:
            ok = False
            lines.extend("  ERROR " + e for e in errors[:20])
        if not ratio_ok:
            ok = False
            lines.append(f"  ERROR split ratio out of tolerance for {name}")
        if set(tier_counts) != TIERS:
            ok = False
            lines.append(f"  ERROR missing tiers in {name}: {TIERS - set(tier_counts)}")

    return ok, "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/synthetic"))
    args = parser.parse_args()
    ok, report = validate_dataset(args.data)
    print(report)
    # exit code 0 se tutto ok, 1 se ci sono errori (utile in script/CI)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
