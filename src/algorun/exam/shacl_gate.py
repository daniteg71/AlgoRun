"""Il gate SHACL e la lettura del target dall'ontologia.

Due funzioni senza dipendenze dai sensori, usate dalla Data Refinery e dal
recommender:
  - validate(): nessuna tripla entra nel Knowledge Graph senza passare da qui;
  - acoustic_target(): interroga l'ontologia (SPARQL) per il target prescritto
    da uno stato di sforzo. La conoscenza sta nell'ontologia; il codice la legge.
"""
from __future__ import annotations

from pyshacl import validate as shacl_validate
from rdflib import Graph

from algorun.ontology.loader import AR, load_ontology, load_shapes


def validate(graph: Graph) -> tuple[bool, str]:
    """Gate SHACL: ontologia fusa nei dati, inferenza SPENTA (closed world).

    Con l'inferenza accesa le violazioni di dominio verrebbero "classificate"
    invece che respinte — per questo il corso impone SHACL come constraint gate.
    """
    merged = graph + load_ontology().graph
    conforms, _, report = shacl_validate(
        data_graph=merged, shacl_graph=load_shapes(), inference="none")
    return conforms, report


_TARGET_QUERY = """
PREFIX ar: <http://algorun.org/ontology#>
SELECT ?bpmMin ?bpmMax ?enMin ?enMax WHERE {
    ?effort ar:prescribesTarget ?t .
    ?t ar:targetBpmMin ?bpmMin ; ar:targetBpmMax ?bpmMax ;
       ar:targetEnergyMin ?enMin ; ar:targetEnergyMax ?enMax .
}"""


def acoustic_target(effort_state: str) -> dict:
    """Chiede all'ontologia quale target (banda BPM/energia) prescrive l'effort."""
    g = load_ontology().graph
    rows = list(g.query(_TARGET_QUERY, initBindings={"effort": AR[effort_state]}))
    r = rows[0]
    return {"bpm_min": float(r[0]), "bpm_max": float(r[1]),
            "energy_min": float(r[2]), "energy_max": float(r[3])}
