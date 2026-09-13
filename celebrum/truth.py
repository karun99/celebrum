"""Truth Engine - the 'Satya' (truth) component of Celebrum.

Inspired by SatyaSandha AI (matruswara), every claim Celebrum recalls from
memory carries a *veracity* score built from:
  * source triangulation - how many independent sources corroborate a topic,
  * contradiction pressure  - how many formal CONTRADICTS synapses oppose it,
  * evidential support     - PGMem-style strength of evidence edges.

The Truth Index is a global health signal for the memory that the Guardrail
Engine can act on (e.g., flag drift or propose a contradiction review).
"""

from __future__ import annotations

from .memory import MemoryGraph, tokenize, json_loads_meta

PRIOR = 0.5


class TruthEngine:
    """Per-neuron veracity + global truth index."""

    def __init__(self, graph: MemoryGraph):
        self.graph = graph

    def topic(self, content) -> str:
        toks = tokenize(content)
        return " ".join(toks[:6]) if toks else "unknown"

    def veracity(self, node) -> float:
        """Score in [0,1] for a single neuron."""
        content = node["content"] or ""
        conf = node.get("confidence", 0.5) or 0.5
        t = self.topic(content)

        # triangulation: distinct sources recalling the same topic
        sources = set()
        for r in self.graph.store.all_nodes():
            if r["node_id"] == node["node_id"]:
                continue
            if self.topic(r["content"] or "") == t and r["source"]:
                sources.add(r["source"])
        support = len(sources) / max(1.0, len(sources))

        # contradiction pressure
        contrad = 0
        for e in self.graph.store.contradiction_edges():
            if e["src"] == node["node_id"] or e["dst"] == node["node_id"]:
                contrad += 1

        # evidential support (PGMem)
        evidence = 0
        for e in self.graph.store.edges_for(node["node_id"]):
            if e["rel"] in ("evidence_for", "supports", "source_of"):
                evidence += 1

        v = PRIOR + 0.25 * support + 0.10 * min(evidence, 3.0) - 0.30 * contrad
        return round(max(0.0, min(1.0, v * (0.5 + 0.5 * conf))), 3)

    def index(self) -> dict:
        """Global Truth Index + contradiction health."""
        nodes = self.graph.store.all_nodes()
        if not nodes:
            return {"truth_index": 1.0, "veracity_layer": 0, "contradiction_ratio": 0.0, "status": "empty"}
        veracity = []
        for n in nodes:
            if n["kind"] in ("fact", "preference", "note", "relationship"):
                veracity.append(self.veracity(dict(n)))
        ratio = self.graph.contradiction_ratio()
        truth_index = (sum(veracity) / len(veracity)) * (1.0 - 0.5 * ratio) if veracity else 1.0
        status = "solid" if truth_index >= 0.75 else ("fragile" if truth_index >= 0.5 else "at_risk")
        return {
            "truth_index": round(truth_index, 3),
            "veracity_layer": len(veracity),
            "contradiction_ratio": round(ratio, 3),
            "status": status,
        }

    def flagged(self) -> list:
        """Neurons whose veracity or contradiction pressure warrants review."""
        flagged = []
        for n in self.graph.store.all_nodes():
            v = self.veracity(dict(n))
            if v < 0.45:
                flagged.append({"id": n["node_id"], "content": n["content"],
                                "kind": n["kind"], "veracity": v})
        return flagged