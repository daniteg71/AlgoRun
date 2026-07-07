"""La Data Refinery: testo libero -> triple RDF, con gli algoritmi baseline
del corso (Rule 3 di GUIDELINES.md).

Pipeline in ordine fisso (dal corso):
    testo -> Tokenizzazione + Lemmatizzazione (spaCy)
          -> Entity & Mention Detection (riuso di nlp.dictionary_extract)
          -> Candidate Relation Extraction (QUESTO modulo: trigger + distanza)
          -> Semantic Grounding (SHACL, riuso di pipeline.validate)
          -> RDF Knowledge Graph

Perché trigger+distanza e non GLiREL: le nostre relazioni sono determinate
dallo schema (domain/range dell'ontologia), quindi generare candidati
vincolati dallo schema è più semplice, deterministico e senza dipendenze
pesanti — decisione già presa e registrata in ALGORITHMS.md.

L'algoritmo, passo per passo:
  1. tokenizza il testo (per calcolare le distanze in token, non in caratteri);
  2. per ogni trigger noto (dal `relation_dictionary()` dell'ontologia) trovato
     nel testo, prende la sua posizione;
  3. cerca, entro una finestra di ±10 token dal trigger, un'entità compatibile
     col DOMAIN della relazione (soggetto) e una compatibile col RANGE
     (oggetto) — il filtro domain/range letto dall'ontologia scarta da solo
     le coppie senza senso;
  4. se il dominio è una classe "senza nome" nel testo (es. WorkoutSession:
     nessuna frase dice mai "la sessione si chiama X"), si usa un nodo
     CANONICO — assumiamo un'unica sessione per documento, esattamente come
     fa il generatore del dataset sintetico.

LIMITI NOTI (da documentare, come richiede esplicitamente la Rule 3):
  - **Vocabolario chiuso**: titoli di canzoni, nomi di playlist, generi (come
    stringhe letterali) e nomi dei runner NON sono individui dell'ontologia
    — non hanno una voce nel dizionario, quindi ogni relazione con quell'
    entità come endpoint (suitsPhase, hasGenre, performsSession, includedIn,
    containsSong, builtForSession...) è strutturalmente irrecuperabile da
    questa baseline. Misurato sul dataset: ~60% delle triple gold ricadono
    in questo caso — non è un bug della logica di pairing, è un limite di
    copertura del NER baseline.
  - **Nodi impliciti senza nome minabile**: `recordsReading` collega la
    sessione a una lettura HR/cadenza mai nominata nel testo (solo un
    numero) — non viene minata, quindi queste triple restano FN.
  - **Bias sul trigger più vicino**: se un trigger governa più coppie
    soggetto/oggetto nello stesso passaggio (tier "nested"), la baseline ne
    cattura solo la coppia più vicina — basso recall atteso su quel tier.

Demo:  python -m algorun.refinery --dataset data/synthetic/test.jsonl
"""

from __future__ import annotations

import argparse
import json
from functools import lru_cache
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

from algorun.exam.nlp import dictionary_extract
from algorun.ontology.loader import AR, load_ontology
from algorun.exam.shacl_gate import validate

EX = Namespace("http://algorun.org/data#")

# finestra di distanza (in token) attorno al trigger, come da Rule 3
DISTANCE_WINDOW = 10

# classi "senza nome nel testo": ogni documento ne ha un'unica istanza
# implicita, rappresentata da un nodo canonico invece che cercarla nel testo.
CANONICAL_TYPES = {str(AR.WorkoutSession)}


_NLP = None  # modello spaCy, caricato pigramente una sola volta


def _spacy_model():
    global _NLP
    if _NLP is None:
        import spacy
        _NLP = spacy.load("en_core_web_sm")
    return _NLP


def tokenize(text: str):
    """Tokenizzazione + lemmatizzazione (spaCy). Ritorna lo spaCy Doc."""
    return _spacy_model()(text)


@lru_cache(maxsize=256)
def _lemma_of_word(word: str) -> str:
    """Lemma di una singola parola del trigger — con cache: le parole dei
    trigger sono un vocabolario piccolo e fisso, si rilemmatizzano una volta."""
    return _spacy_model()(word)[0].lemma_.lower()


def _char_to_token_index(doc, char_pos: int) -> int:
    """Converte una posizione a carattere nell'indice del token che la contiene
    (o il più vicino, se cade a metà di un token)."""
    span = doc.char_span(char_pos, char_pos + 1, alignment_mode="expand")
    if span is not None and len(span) > 0:
        return span[0].i
    return len(doc) - 1


def _canonical_key(type_iri: str) -> tuple[str, str]:
    """Chiave del nodo canonico per una classe senza nome nel testo."""
    return ("CANONICAL", type_iri)


# tolleranza (in token) fra una parola del trigger e la successiva: i trigger
# multi-parola dell'ontologia ("includes phase") raramente compaiono contigui
# nel testo generato ("includes A HARD phase") — le parole del trigger si
# cercano quindi in ordine, non necessariamente una attaccata all'altra.
TRIGGER_WORD_SLACK = 4


def _trigger_occurrences(lemmas: list[str], trigger_words: list[str]) -> list[int]:
    """Posizioni (indice del PRIMO token) in cui tutte le parole del trigger
    compaiono in ordine, entro TRIGGER_WORD_SLACK token l'una dall'altra."""
    occurrences = []
    for i, lemma in enumerate(lemmas):
        if lemma != trigger_words[0]:
            continue
        last_pos, matched = i, True
        for word in trigger_words[1:]:
            window_end = min(len(lemmas), last_pos + 1 + TRIGGER_WORD_SLACK)
            found = next((k for k in range(last_pos + 1, window_end)
                         if lemmas[k] == word), None)
            if found is None:
                matched = False
                break
            last_pos = found
        if matched:
            occurrences.append(i)
    return occurrences


def extract_relations(text: str, entities: list[dict]) -> list[tuple]:
    """Passo 3: trigger + distanza, filtrato da domain/range.

    `entities` è l'output di `nlp.dictionary_extract(text)`. Ritorna triple
    candidate (subj_key, predicate_iri, obj_key) dove subj_key/obj_key sono
    o l'IRI di un'entità testuale, o la chiave canonica (vedi sopra). Il
    trigger si cerca sui LEMMI (passo di lemmatizzazione) così coglie anche
    forme flesse ("targeted"/"targets" -> lemma "target").
    """
    schema = load_ontology()
    doc = tokenize(text)
    lemmas = [t.lemma_.lower() for t in doc]

    # entità con il loro indice di token, per il calcolo della distanza
    ents_by_token = [(_char_to_token_index(doc, e["start"]), e) for e in entities]

    candidates: list[tuple] = []
    for surface, prop_iri in schema.relation_dictionary():   # longest-first
        spec = schema.object_properties[prop_iri]
        if spec.domain is None or spec.range is None:
            continue
        trigger_words = [_lemma_of_word(w) for w in surface.split()]

        for trigger_tok in _trigger_occurrences(lemmas, trigger_words):
            window = [(abs(tok - trigger_tok), tok, e) for tok, e in ents_by_token
                     if abs(tok - trigger_tok) <= DISTANCE_WINDOW]
            window.sort(key=lambda w: w[0])   # più vicino al trigger prima

            subj = _nearest_of_type(window, str(spec.domain))
            obj = _nearest_of_type(window, str(spec.range))

            if str(spec.domain) in CANONICAL_TYPES:
                subj = _canonical_key(str(spec.domain))
            if str(spec.range) in CANONICAL_TYPES:
                obj = _canonical_key(str(spec.range))

            if subj is not None and obj is not None and subj != obj:
                # str(prop_iri): rdflib.URIRef non è "==" a una str identica
                # (rdflib.term.URIRef.__eq__ rifiuta il confronto con str
                # anche se ne è sottoclasse) — le triple gold nel JSONL sono
                # stringhe semplici, quindi si confronta stringa con stringa.
                candidates.append((subj, str(prop_iri), obj))
    return candidates


def _nearest_of_type(window: list[tuple], type_iri: str) -> str | None:
    for _, _, e in window:
        if e["type_iri"] == type_iri:
            return e["iri"]
    return None


def _all_of_type(window: list[tuple], type_iri: str) -> list[str]:
    return [e["iri"] for _, _, e in window if e["type_iri"] == type_iri]


def extract_candidates(text: str, entities: list[dict]) -> list[tuple]:
    """Generatore PAIRWISE per il validator (M4) — Architecture A del corso.

    A differenza della baseline (`extract_relations`, che richiede un trigger
    e sceglie la coppia più vicina), qui si SOVRA-GENERA di proposito: ogni
    coppia di entità compatibile con domain/range di OGNI relazione diventa
    un candidato, senza cercare trigger. Misurato su 100 record di train:
    47 positivi + 199 negativi (ceiling recall 0.39 vs 0.14 della baseline)
    — è questo che dà al validator supervisionato un compito reale, la
    "dissociazione generatore/validator" richiesta dal corso.
    """
    schema = load_ontology()
    keys = [(e["iri"], e["type_iri"]) for e in entities]
    keys.append((_canonical_key(str(AR.WorkoutSession)), str(AR.WorkoutSession)))

    candidates: list[tuple] = []
    for prop_iri, spec in schema.object_properties.items():
        if spec.domain is None or spec.range is None:
            continue
        dom, rng = str(spec.domain), str(spec.range)
        for s_iri, s_type in keys:
            for o_iri, o_type in keys:
                if s_iri != o_iri and s_type == dom and o_type == rng:
                    candidates.append((s_iri, str(prop_iri), o_iri))
    return list(dict.fromkeys(candidates))   # dedup preservando l'ordine


def build_graph(text: str) -> tuple[Graph, list[tuple]]:
    """Orchestrazione: entità -> relazioni candidate -> cancello SHACL.

    Ritorna (grafo RDF validato, lista delle triple candidate). Le triple con
    un nodo canonico usano un IRI segnaposto stabile (EX.session) — non
    influisce sulla validazione SHACL, che guarda solo tipo e proprietà.
    """
    entities = dictionary_extract(text)
    candidates = extract_relations(text, entities)

    g = Graph()
    g.bind("ar", AR)
    placeholder = {}   # chiave canonica -> nodo RDF stabile in questo grafo

    def resolve(key) -> URIRef:
        if isinstance(key, tuple):   # nodo canonico
            if key not in placeholder:
                node = EX.session
                g.add((node, RDF.type, URIRef(key[1])))
                placeholder[key] = node
            return placeholder[key]
        return URIRef(key)

    for subj, prop_iri, obj in candidates:
        g.add((resolve(subj), URIRef(prop_iri), resolve(obj)))

    validate(g)   # il cancello SHACL: qui serve solo a rifiutare l'inammissibile
    return g, candidates


# ----------------------------------------------------------------- benchmark

def _gold_key(entity: dict) -> tuple[str, str] | str:
    """Stessa convenzione di chiave usata dal predetto: IRI se il testo la
    nomina, nodo canonico altrimenti (Rule 4: confronto Predicted vs Actual)."""
    if entity.get("mentioned"):
        return entity["iri"]
    return _canonical_key(entity["type_iri"])


def _gold_triples(record: dict) -> set[tuple]:
    by_id = {e["id"]: e for e in record["entities"]}
    return {(_gold_key(by_id[s]), p, _gold_key(by_id[o]))
            for s, p, o in record["triples"]}


def _predicted_triples(text: str) -> set[tuple]:
    _, candidates = build_graph(text)
    return set(candidates)


def _prf1(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": round(precision, 3), "recall": round(recall, 3),
            "f1": round(f1, 3), "tp": tp, "fp": fp, "fn": fn}


def evaluate_on_dataset(path: Path | str, limit: int | None = None) -> dict:
    """Valutazione grafo-predetto-vs-grafo-reale (Phase 6 / Rule 4).

    Ritorna {"overall": prf1, "per_tier": {...}, "per_relation": {...}} —
    le tre viste richieste per il report: complessiva, per livello di
    complessità, e per tipo di relazione (isola il limite del vocabolario
    chiuso spiegato nel docstring del modulo). `limit` serve solo nei test,
    per non rileggere l'intero dataset ad ogni esecuzione della suite.
    """
    records = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    if limit is not None:
        records = records[:limit]

    buckets: dict[str, list[int]] = {}   # chiave -> [tp, fp, fn]

    def add(key: str, gold: set, pred: set):
        tp, fp, fn = buckets.setdefault(key, [0, 0, 0])
        buckets[key] = [tp + len(pred & gold), fp + len(pred - gold), fn + len(gold - pred)]

    for rec in records:
        gold = _gold_triples(rec)
        pred = _predicted_triples(rec["text"])
        add("overall", gold, pred)
        add(f"tier:{rec['tier']}", gold, pred)
        predicates = {t[1] for t in gold} | {t[1] for t in pred}
        for p in predicates:   # una sola volta per predicato, non per tripla
            add(f"relation:{p.split('#')[-1]}", {t for t in gold if t[1] == p},
                {t for t in pred if t[1] == p})

    result = {"overall": _prf1(*buckets.pop("overall"))}
    result["per_tier"] = {k.split(":", 1)[1]: _prf1(*v) for k, v in buckets.items()
                          if k.startswith("tier:")}
    result["per_relation"] = {k.split(":", 1)[1]: _prf1(*v) for k, v in buckets.items()
                              if k.startswith("relation:")}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="data/synthetic/test.jsonl")
    args = parser.parse_args()

    result = evaluate_on_dataset(args.dataset)
    print(f"OVERALL   {result['overall']}")
    print("\nPer tier:")
    for tier, m in result["per_tier"].items():
        print(f"  {tier:15} P={m['precision']:.2f} R={m['recall']:.2f} F1={m['f1']:.2f}")
    print("\nPer relation:")
    for rel, m in sorted(result["per_relation"].items()):
        print(f"  {rel:20} P={m['precision']:.2f} R={m['recall']:.2f} F1={m['f1']:.2f}")


if __name__ == "__main__":
    main()
