"""Celebrum engine - the facade that wires Store + MemoryGraph + PersonaModel +
TruthEngine + GuardrailEngine + PTM together. Consumed by CLI, GUI and MCP.

All state lives under one SQLite file (default ~/.celebrum/celebrum.db) so the
whole brain travels with one folder (Linux, macOS, Windows, Android/Termux,
Raspberry Pi).
"""

from __future__ import annotations

import json
import os

from . import __version__
from .guardrails import GuardrailEngine
from .ingest import Ingestor
from .memory import MemoryGraph, tokenize
from .persona import PersonaModel
from .simulate import Simulation
from .store import Store, now_iso
from .tensor import PersonalTensorMemory
from .truth import TruthEngine


def default_home() -> str:
    base = os.environ.get("CELEBRUM_HOME")
    if base:
        return base
    return os.path.join(os.path.expanduser("~"), ".celebrum")


class Celebrum:
    def __init__(self, home: str | None = None, db: str | None = None):
        self.home = home or default_home()
        self.db_path = db or os.path.join(self.home, "celebrum.db")
        os.makedirs(self.home, exist_ok=True)
        self.store = Store(self.db_path)
        self.graph = MemoryGraph(self.store)
        self.guardrails = GuardrailEngine(self.store)
        self.ingestor = Ingestor(self.graph)
        self._load_state()

    # ---------------- state ------------------------------------------------
    def _load_state(self):
        pd = self.store.get_meta("persona")
        self.persona = PersonaModel.from_dict(pd) if pd else PersonaModel()
        ptm_bytes = self.store.get_meta("ptm_raw")
        try:
            self.tensor = PersonalTensorMemory.from_bytes(bytes(ptm_bytes)) if ptm_bytes else PersonalTensorMemory()
        except Exception:
            self.tensor = PersonalTensorMemory()
        self.snapshots = self.store.get_meta("persona_snapshots", [])
        if not self.store.get_meta("booted"):
            self.store.set_meta("booted", True)
            self.store.log("celebrum", "boot", risk="low",
                           details={"version": __version__, "home": self.home}, result="ok")

    def _save_persona(self):
        self.store.set_meta("persona", self.persona.to_dict())

    def _save_tensor(self):
        self.store.set_meta("ptm_raw", list(self.tensor.to_bytes()))

    # ---------------- learning ---------------------------------------------
    def learn(self, log=True):
        """Re-aggregate the persona from the memory graph and refresh the PTM."""
        old_vec = self.persona.to_vector()
        self.persona.build(self.graph)
        self._ground_persona()
        self._save_persona()
        self._snapshot(old_vec)
        self.tensor.update_from_text(" ".join((r["content"] or "")
                                              for r in self.graph.store.all_nodes()), weight=0.5)
        self._save_tensor()
        if log:
            self.store.log("celebrum", "learn", risk="low",
                           details={"persona_version": self.persona.version}, result="ok")

    def _ground_persona(self):
        """PGMem: give persona-level value signals typed evidence edges so they
        are traceable to the preference memories that justify them."""
        from .memory import json_loads_meta
        for r in self.graph.store.all_nodes():
            if r["kind"] != "preference":
                continue
            meta = json_loads_meta(r["meta"])
            topic = meta.get("topic")
            if not topic:
                continue
            sentiment = float(meta.get("sentiment", 0.0))
            if abs(sentiment) < 0.5:
                continue
            target = self._ensure_value_neuron(topic, r["node_id"])
            self.graph.add_synapse(r["node_id"], target, "evidence_for", 1.0)

    def _ensure_value_neuron(self, topic, pref_id):
        for r in self.graph.store.all_nodes():
            if r["kind"] == "value":
                from .memory import json_loads_meta
                if json_loads_meta(r["meta"]).get("topic") == topic:
                    return r["node_id"]
                if (r["content"] or "").strip().lower() == topic.lower():
                    return r["node_id"]
        nid = self.graph.add_neuron("value", topic, source="celebrum",
                                    confidence=0.7, meta={"topic": topic, "signal": "learned_value"})
        self.graph.add_synapse(nid, pref_id, "source_of", 1.0)
        return nid

    def _snapshot(self, old_vec):
        self.snapshots.append({
            "ts": now_iso(),
            "old": [round(v, 5) for v in old_vec],
            "new": [round(v, 5) for v in self.persona.to_vector()],
            "version": self.persona.version,
        })
        self.snapshots = self.snapshots[-24:]
        self.store.set_meta("persona_snapshots", self.snapshots)

    # ---------------- ingest -----------------------------------------------
    def ingest_duet(self, duet, consent=True, source="duet") -> dict:
        n = self.ingestor.ingest_duet(duet, consent=consent, source=source)
        self.learn()
        self.store.log("ingest", "ingest_duet", risk="low",
                       details={"neurons": n, "consent": consent}, result="ok")
        return {"neurons": n}

    def ingest_web(self, url, consent=True) -> dict:
        n = self.ingestor.ingest_web(url, consent=consent)
        self.learn()
        self.store.log("ingest", "ingest_web", risk="medium",
                       details={"url": url, "neurons": n, "consent": consent}, result="ok")
        return {"neurons": n}

    def ingest_html(self, filename, consent=True) -> dict:
        n = self.ingestor.ingest_html_file(filename, consent=consent)
        self.learn()
        self.store.log("ingest", "ingest_html", risk="low",
                       details={"filename": filename, "neurons": n, "consent": consent}, result="ok")
        return {"neurons": n}

    # ---------------- operations ---------------------------------------------
    def recall(self, query, k=5, identity=True, log=True):
        r = self.graph.recall(query, k=k, identity=identity)
        if log:
            self.store.log("user", "recall", risk="low",
                           details={"query": query[:120], "hits": len(r)}, result="ok")
        return r

    def simulate(self, scenario):
        sim = Simulation(self.persona, self.graph)
        r = sim.run(scenario)
        self.store.log("user", "simulate", risk="low",
                       details={"scenario": scenario[:120], "stance": r["stance"]}, result="ok")
        return r

    def propose(self):
        proposals = self.guardrails.propose(self.persona, self.truth().index())
        self.store.log("celebrum", "propose", risk="low",
                       details={"proposals": len(proposals)}, result="ok")
        return proposals

    def approve(self, guardrail_id, by="local-user"):
        g = self.guardrails.approve(guardrail_id, approved_by=by)

        return g

    def reject(self, guardrail_id, by="local-user"):
        return self.guardrails.reject(guardrail_id, approved_by=by)

    def revert(self, guardrail_id, by="local-user"):
        return self.guardrails.revert(guardrail_id, approved_by=by)

    def apply_proposal(self, proposal, by="local-user"):
        return self.guardrails.apply(proposal, approved_by=by)

    def truth(self) -> TruthEngine:
        return TruthEngine(self.graph)

    def validate(self):
        from . import validate as v
        return v.run(self)

    def correctness_action(self, node_id, approve=True):
        """User verdict on a recalled neuron (FR-3.5 feedback / truth layer)."""
        n = self.graph.neuron(node_id)
        if n is None:
            raise KeyError(node_id)
        weight = 1.0 if approve else -1.0
        node_ids = [r["id"] for r in self.graph.recall(n["content"], k=1, threshold=0.0)]
        for nid in node_ids:
            self.graph.add_synapse(nid, nid, "evidence_for", max(1.0, weight), ts=now_iso())
        self.store.log("user", "feedback", risk="low",
                       details={"node": node_id, "approve": approve}, result="ok")
        return {"node": n["content"], "state": "affirmed" if approve else "contested"}

    def snapshot(self) -> dict:
        return {
            "version": __version__,
            "stats": self.graph.stats(),
            "truth": self.truth().index(),
            "persona": self.persona.to_dict(),
            "guardrails_active": len(self.guardrails.active()),
            "guardrails_total": len(self.guardrails.all()),
            "tensor": self.tensor.summary(),
            "drift_snapshots": len(self.snapshots),
            "home": self.home,
        }