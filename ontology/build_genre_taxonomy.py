"""Genera la tassonomia dei generi musicali (ontology/genres.ttl).

I 113 generi del dataset vengono organizzati in un albero
leaf -> famiglia -> super-famiglia -> radice via skos:broader: la distanza
sul grafo diventa una misura di vicinanza semantica fra generi (usata dallo
scorer per il termine genere-utente).

L'affinita' genere->sforzo (ar:genreSuitsEffort) NON e' inventata: e' lo sforzo
dominante osservato nella colonna `matches_effort` del dataset per quel genere.

Uso: python ontology/build_genre_taxonomy.py [percorso_csv]
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pandas as pd

# Albero: super-famiglia -> famiglia -> generi foglia. Ogni genere una volta sola.
TAXONOMY: dict[str, dict[str, list[str]]] = {
    "rock": {
        "rock_core": ["rock", "alt-rock", "alternative", "hard-rock",
                      "psych-rock", "rock-n-roll", "rockabilly", "british", "guitar"],
        "indie": ["indie", "indie-pop", "power-pop", "grunge", "emo"],
        "punk": ["punk", "punk-rock", "ska", "garage"],
        "jrock": ["j-rock"],
    },
    "metal": {
        "metal_core": ["metal", "heavy-metal", "black-metal", "death-metal",
                       "metalcore", "grindcore", "hardcore", "industrial", "goth"],
    },
    "electronic": {
        "house": ["house", "deep-house", "chicago-house", "progressive-house", "disco"],
        "techno": ["techno", "detroit-techno", "minimal-techno"],
        "bass": ["dubstep", "drum-and-bass", "breakbeat", "hardstyle", "idm", "dub"],
        "edm": ["edm", "electro", "electronic", "trance", "club", "dance"],
        "downtempo": ["trip-hop", "ambient"],
    },
    "pop": {
        "pop_core": ["pop", "synth-pop", "pop-film"],
        "dance_pop": ["party", "happy"],
        "asian_pop": ["j-pop", "k-pop", "cantopop", "mandopop", "j-idol", "j-dance"],
    },
    "urban": {
        "hiphop": ["hip-hop", "r-n-b", "soul", "funk", "groove"],
    },
    "jazz_blues": {
        "jazz_blues": ["jazz", "blues", "bluegrass", "honky-tonk", "gospel"],
    },
    "folk": {
        "folk_acoustic": ["folk", "acoustic", "singer-songwriter", "country"],
    },
    "classical": {
        "classical_core": ["classical", "opera", "piano", "new-age", "show-tunes"],
    },
    "latin": {
        "latin_core": ["latin", "latino", "reggaeton", "salsa", "samba", "mpb",
                       "forro", "pagode", "sertanejo", "brazil", "tango", "spanish",
                       "dancehall", "reggae", "afrobeat"],
    },
    "world": {
        "world_regional": ["world-music", "indian", "iranian", "turkish", "malay",
                           "german", "swedish", "french"],
    },
    "functional": {
        "mood": ["chill", "sad", "sleep", "study", "romance", "comedy"],
        "media": ["anime", "disney", "children", "kids"],
    },
}

EFFORT_IRI = {
    "LowEffort": "ar:LowEffort", "TargetEffort": "ar:TargetEffort",
    "HighEffort": "ar:HighEffort", "VeryHighEffort": "ar:VeryHighEffort",
}


def slug(name: str) -> str:
    return name.replace("-", "_")


def dominant_effort(df: pd.DataFrame) -> dict[str, str]:
    """Sforzo modale per genere, letto dalla colonna multi-valore matches_effort."""
    out: dict[str, str] = {}
    for genre, sub in df.groupby("genre"):
        counts: Counter[str] = Counter()
        for cell in sub["matches_effort"].dropna().astype(str):
            counts.update(p for p in cell.split(";") if p in EFFORT_IRI)
        if counts:
            out[str(genre)] = counts.most_common(1)[0][0]
    return out


def build(csv_path: Path) -> str:
    df = pd.read_csv(csv_path, usecols=["genre", "matches_effort"])
    dataset_genres = set(df["genre"].dropna().astype(str).unique())

    mapped = {g for fams in TAXONOMY.values() for gs in fams.values() for g in gs}
    missing = dataset_genres - mapped
    extra = mapped - dataset_genres
    if missing or extra:
        raise SystemExit(f"Tassonomia disallineata dal dataset. Mancano: {sorted(missing)}. Di troppo: {sorted(extra)}.")

    effort = dominant_effort(df)

    lines = [
        "# GENERATO da ontology/build_genre_taxonomy.py — non editare a mano.",
        "@prefix ar:   <http://algorun.org/ontology#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
        "",
        "ar:MusicGenreScheme a skos:ConceptScheme ; rdfs:label \"music genre taxonomy\" .",
        "ar:g_root a ar:Genre, skos:Concept ; rdfs:label \"music\" ; skos:inScheme ar:MusicGenreScheme .",
        "",
    ]
    for sf, families in TAXONOMY.items():
        lines.append(f"ar:gs_{slug(sf)} a ar:Genre, skos:Concept ; rdfs:label \"{sf}\" ; "
                     f"skos:broader ar:g_root ; skos:topConceptOf ar:MusicGenreScheme .")
        for fam, genres in families.items():
            lines.append(f"ar:gf_{slug(fam)} a ar:Genre, skos:Concept ; rdfs:label \"{fam}\" ; "
                         f"skos:broader ar:gs_{slug(sf)} .")
            for g in genres:
                eff = effort.get(g)
                suit = f" ; ar:genreSuitsEffort {EFFORT_IRI[eff]}" if eff else ""
                lines.append(f"ar:g_{slug(g)} a ar:Genre, skos:Concept ; rdfs:label \"{g}\" ; "
                             f"skos:broader ar:gf_{slug(fam)}{suit} .")
        lines.append("")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    csv = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parents[1] / "data/music/songs.csv"
    ttl = build(csv)
    out = Path(__file__).parent / "genres.ttl"
    out.write_text(ttl)
    n = ttl.count("a ar:Genre")
    print(f"Scritto {out} — {n} concetti (generi + famiglie + super-famiglie).")
