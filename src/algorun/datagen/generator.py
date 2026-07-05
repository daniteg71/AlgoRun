"""Tiered synthetic dataset generator (GUIDELINES.md Rule 2).

Instantiates the LLM-authored templates in ``templates.py`` with surface
forms drawn from the ontology label dictionary — never hardcoded strings —
and emits gold-annotated JSONL records with a stratified 70/15/15
train/validation/test split.

Record schema (one JSON object per line):
    {
      "id": "rec_000123",
      "tier": "explicit" | "implicit" | "long_distance" | "nested",
      "text": "...",
      "entities": [
        {"id": "e0", "iri": "...", "type_iri": "...",
         "surface": "...", "start": 12, "end": 25, "mentioned": true},
        ...                        # implicit nodes have no span, mentioned=false
      ],
      "triples": [["e0", "http://algorun.org/ontology#performsSession", "e1"], ...]
    }

Usage:
    python -m algorun.datagen.generator --out data/synthetic --per-tier 200
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from rdflib import URIRef
from rdflib.namespace import RDF, RDFS, SKOS

from algorun.ontology.loader import AR, OntologySchema, load_ontology

from . import templates as T

DATA = "http://algorun.org/data#"
SPLIT_RATIOS = (0.70, 0.15, 0.15)  # train / val / test — Rule 2, non-negotiable


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text.lower()).strip("_")


def _individual_surfaces(schema: OntologySchema, cls: URIRef,
                         canonical: bool) -> list[tuple[URIRef, str]]:
    """(individual IRI, surface form) pairs for all individuals of a class.

    ``canonical=True`` yields only rdfs:label forms (explicit tier);
    otherwise every skos:altLabel synonym is offered too (implicit tier).
    """
    pairs: list[tuple[URIRef, str]] = []
    for ind in schema.graph.subjects(RDF.type, cls):
        if not isinstance(ind, URIRef) or ind not in schema.individuals:
            continue
        labels = [str(v).lower() for v in schema.graph.objects(ind, RDFS.label)]
        alts = [str(v).lower() for v in schema.graph.objects(ind, SKOS.altLabel)]
        forms = labels if canonical else (alts or labels)
        pairs.extend((ind, form) for form in forms)
    return pairs


class RecordBuilder:
    """Fills one template into a fully annotated record."""

    def __init__(self, schema: OntologySchema, rng: random.Random):
        self.schema = schema
        self.rng = rng

    def _pick_slots(self, tier: str) -> dict[str, tuple[str, str, str]]:
        """slot -> (surface, entity IRI, type IRI). Implicit tier prefers
        synonym surface forms; other tiers use canonical labels."""
        canonical = tier != "implicit"
        rng = self.rng
        wtype = rng.choice(_individual_surfaces(self.schema, AR.WorkoutType, canonical))
        phase = rng.choice(_individual_surfaces(self.schema, AR.TrainingPhase, canonical))
        zone = rng.choice(_individual_surfaces(self.schema, AR.EffortState, canonical))
        runner = rng.choice(T.RUNNER_NAMES)
        song = rng.choice(T.SONG_TITLES)
        genre = rng.choice(T.GENRES)
        playlist = rng.choice(T.PLAYLIST_NAMES)
        return {
            "wtype": (wtype[1], str(wtype[0]), str(AR.WorkoutType)),
            "phase": (phase[1], str(phase[0]), str(AR.TrainingPhase)),
            "zone": (zone[1], str(zone[0]), str(AR.EffortState)),
            "runner": (runner, DATA + "runner_" + _slug(runner), str(AR.Runner)),
            "song": (song, DATA + "song_" + _slug(song), str(AR.Song)),
            "genre": (genre, DATA + "genre_" + _slug(genre), str(AR.Genre)),
            "playlist": (playlist, DATA + "playlist_" + _slug(playlist), str(AR.Playlist)),
            "hr": (rng.choice(T.HR_VALUES), None, None),
            "cad": (rng.choice(T.CADENCE_VALUES), None, None),
        }

    # slots that exist as graph nodes but never as text spans
    IMPLICIT_NODES = {
        "session_implicit": str(AR.WorkoutSession),
        "hr_reading": str(AR.HeartRateReading),
        "cad_reading": str(AR.CadenceReading),
    }

    def build(self, rec_id: str, tier: str, template: dict) -> dict:
        slots = self._pick_slots(tier)
        text = template["text"].format(**{k: v[0] for k, v in slots.items()})

        entities: list[dict] = []
        entity_ids: dict[str, str] = {}   # slot -> "eN"

        def register(slot: str, iri: str, type_iri: str,
                     surface: str | None) -> str:
            if slot in entity_ids:
                return entity_ids[slot]
            eid = f"e{len(entities)}"
            entity_ids[slot] = eid
            entry = {"id": eid, "iri": iri, "type_iri": type_iri,
                     "mentioned": surface is not None}
            if surface is not None:
                # annotate every occurrence of the surface form
                spans, start = [], 0
                lowered, needle = text.lower(), surface.lower()
                while (idx := lowered.find(needle, start)) != -1:
                    spans.append([idx, idx + len(needle)])
                    start = idx + len(needle)
                entry["surface"] = surface
                entry["spans"] = spans
            entities.append(entry)
            return eid

        triples_out: list[list[str]] = []
        for subj_slot, rel_suffix, obj_slot in template["triples"]:
            rel_iri = str(AR[rel_suffix])
            resolved = []
            for slot in (subj_slot, obj_slot):
                if slot in self.IMPLICIT_NODES:
                    iri = DATA + f"{slot}_{rec_id}"
                    resolved.append(register(slot, iri, self.IMPLICIT_NODES[slot], None))
                else:
                    surface, iri, type_iri = slots[slot]
                    resolved.append(register(slot, iri, type_iri, surface))
            triples_out.append([resolved[0], rel_iri, resolved[1]])

        return {"id": rec_id, "tier": tier, "text": text,
                "entities": entities, "triples": triples_out}


def generate(per_tier: int, seed: int = 42) -> list[dict]:
    schema = load_ontology()
    rng = random.Random(seed)
    builder = RecordBuilder(schema, rng)
    records: list[dict] = []
    counter = 0
    for tier, tier_templates in T.TEMPLATES.items():
        for _ in range(per_tier):
            template = rng.choice(tier_templates)
            records.append(builder.build(f"rec_{counter:06d}", tier, template))
            counter += 1
    return records


def split_records(records: list[dict], seed: int = 42) -> dict[str, list[dict]]:
    """Stratified-by-tier 70/15/15 split (Rule 2)."""
    rng = random.Random(seed)
    splits: dict[str, list[dict]] = {"train": [], "val": [], "test": []}
    tiers: dict[str, list[dict]] = {}
    for rec in records:
        tiers.setdefault(rec["tier"], []).append(rec)
    for tier_records in tiers.values():
        rng.shuffle(tier_records)
        n = len(tier_records)
        n_train = round(n * SPLIT_RATIOS[0])
        n_val = round(n * SPLIT_RATIOS[1])
        splits["train"].extend(tier_records[:n_train])
        splits["val"].extend(tier_records[n_train:n_train + n_val])
        splits["test"].extend(tier_records[n_train + n_val:])
    return splits


def write_jsonl(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("data/synthetic"))
    parser.add_argument("--per-tier", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    records = generate(args.per_tier, args.seed)
    splits = split_records(records, args.seed)
    for name, recs in splits.items():
        write_jsonl(recs, args.out / f"{name}.jsonl")
        print(f"{name}: {len(recs)} records")


if __name__ == "__main__":
    main()
