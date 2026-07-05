"""Fusione prompt + sensore: chi decide il target quando parlano entrambi.

Prima di questo modulo i due flussi erano separati: nlp.py produce il target
dichiarato dall'utente (quantitativo) e pipeline.py il target dedotto dal
battito (qualitativo). Il buco: un prompt "12 km/h" scavalcava la sicurezza,
perché i vincoli SHACL su HR critico si attivano solo se appliedTargetBpm e
currentHeartRateBpm stanno nello STESSO grafo.

Regole di precedenza (in ordine, la prima che scatta vince):
  1. SICUREZZA  — HR oltre la linea safe-max (93% HRmax): target calmo,
     qualunque cosa dica il prompt.
  2. PROMPT     — quantitativo valido: il BPM chirurgico dichiarato, MA
     ri-validato dal gate SHACL con dentro anche lo stato del corpo; se il
     gate lo respinge si ricade sulla sicurezza.
  3. SENSORE    — prompt qualitativo: si usa il target dedotto dall'effort.

Demo:  python -m algorun.fusion
"""

from __future__ import annotations

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, XSD

from algorun.ontology.loader import AR
from algorun.pipeline import (SAFE_MAX_FRACTION, _demo_window, acoustic_target,
                              decide, validate)
from algorun.nlp import ground

EX = Namespace("http://algorun.org/data#")


def _combined_graph(prompt_bpm: float, current_hr: float,
                    resting_hr: float, max_hr: float) -> Graph:
    """Grafo con TARGET DICHIARATO e STATO DEL CORPO insieme: è questo che
    permette ai vincoli SPARQL-SHACL (HR critico, emergenza) di attivarsi."""
    g = Graph()
    g.bind("ar", AR)

    def dec(v: float) -> Literal:
        return Literal(str(round(v, 1)), datatype=XSD.decimal)

    g.add((EX.runner, RDF.type, AR.Runner))
    g.add((EX.runner, AR.safeMaxHeartRateBpm, dec(max_hr * SAFE_MAX_FRACTION)))
    g.add((EX.runner, AR.restingHeartRateBpm, dec(resting_hr)))
    g.add((EX.runner, AR.maxHeartRateBpm, dec(max_hr)))
    g.add((EX.session, RDF.type, AR.WorkoutSession))
    g.add((EX.session, AR.performedBy, EX.runner))
    g.add((EX.session, AR.currentHeartRateBpm, dec(current_hr)))
    g.add((EX.session, AR.appliedTargetBpm, dec(prompt_bpm)))
    return g


def fuse(prompt_result: dict, sensor_decision: dict,
         resting_hr: float, max_hr: float) -> dict:
    """Arbitra tra target del prompt e target del sensore.

    prompt_result   = output di nlp.ground()      (bpm_target o None)
    sensor_decision = output di pipeline.decide() (effort, target, sicurezza)

    Ritorna {target, source, shacl_ok, note}. `source` dice chi ha vinto:
    "safety" | "prompt" | "sensor".
    """
    hr = sensor_decision["hr"]

    # Regola 1 — la sicurezza vince sempre (già calcolata dal ponte)
    if sensor_decision["forced_recovery"] or hr >= max_hr * SAFE_MAX_FRACTION:
        return {"target": acoustic_target("LowEffort"), "source": "safety",
                "shacl_ok": True,
                "note": "HR oltre la linea safe-max: target calmo forzato"}

    # Regola 2 — prompt quantitativo: BPM chirurgico, ri-validato dal SHACL
    # con lo stato del corpo nello stesso grafo
    bpm_target = prompt_result.get("bpm_target")
    if bpm_target is not None:
        g = _combined_graph(bpm_target["bpm_one_to_one"], hr, resting_hr, max_hr)
        ok, report = validate(g)
        if ok:
            return {"target": bpm_target, "source": "prompt", "shacl_ok": True,
                    "note": "target dichiarato dall'utente, validato dal gate"}
        # il gate ha respinto il target dichiarato -> si ripiega sulla calma
        return {"target": acoustic_target("LowEffort"), "source": "safety",
                "shacl_ok": False,
                "note": "target dichiarato RESPINTO dal gate SHACL"}

    # Regola 3 — prompt qualitativo: decide il sensore
    return {"target": sensor_decision["target"], "source": "sensor",
            "shacl_ok": sensor_decision["shacl_ok"],
            "note": f"nessun numero nel prompt: effort {sensor_decision['effort']}"}


def main() -> None:
    resting_hr, max_hr = 60.0, 195.0
    scenarios = [
        ("I feel tired, something easy", 140),   # qualitativo -> sensore
        ("tempo run at 12 km/h", 140),           # quantitativo sano -> prompt
        ("tempo run at 12 km/h", 185),           # quantitativo + HR critico -> sicurezza
    ]
    for text, hr_level in scenarios:
        prompt = ground(text)
        sensor = decide(_demo_window(hr_level, resting_hr, max_hr),
                        resting_hr, max_hr, "interval")
        f = fuse(prompt, sensor, resting_hr, max_hr)
        t = f["target"]
        band = (f"{t['bpm_one_to_one']}" if "bpm_one_to_one" in t
                else f"{t['bpm_min']:.0f}-{t['bpm_max']:.0f}")
        print(f'"{text}" | HR~{sensor["hr"]:.0f}')
        print(f"  -> vince: {f['source'].upper():7}  target BPM: {band:9}  ({f['note']})\n")


if __name__ == "__main__":
    main()
