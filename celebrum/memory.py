"""Memory Graph - the neuron/synapse graphdb of Celebrum.

Grounding
---------
* PGMem (arXiv 2608.01708): heterogeneous persona-memory graph with typed
  provenance/evidence edges; retrieval ranks signals by evidential validity.
* ID-RAG (MIT Media Lab, arXiv 2509.25299): identity is an explicit retrievable
  knowledge structure; identity context is retrieved and weighted in recall.
* BRIDGE (ICML 2026): tiered half-life decay so fleeting details change fast
  while core personality shifts only slowly (bounded, "cannot drift away
  uncontrollably").
"""

from __future__ import annotations

import math
import re
import uuid
from datetime import datetime, timezone

from .store import Store, now_iso

_TOKEN_RE = re.compile(r"[a-z0-9']+")

# Neuron kinds (event-level memory + persona/identity level)
KINDS = {
    "fact", "note", "preference", "decision", "milestone", "relationship",
    "identity", "value", "trait", "persona_signal",
}

# BRIDGE tiered half-lives (days): core shifts slowly, ephemera decays fast.
HALF_LIFE_DAYS = {
    "note": 15,
    "fact": 30,
    "preference": 120,
    "relationship": 365,
    "decision": 730,
    "milestone": 3650,
    "identity": 7300,
    "value": 7300,
    "trait": 7300,
    "persona_signal": 7300,
}

# Identity-adjacent kinds used by the ID-RAG grounding weight.
IDENTITY_KINDS = {"identity", "value", "trait", "relationship"}


def tokenize(text: str):
    """Lowercased alphanumeric tokens (bag of words)."""
    if not text:
        return []
    return _TOKEN_RE.findall(str(text).lower())


def _age_days(ts: str) -> float:
    try:
        dt = datetime.fromisoformat(str(ts))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0)
    except (ValueError, TypeError):
        return 0.0


def decay(age_days: float, kind: str) -> float:
    """BRIDGE-style exponential decay with tiered half-life."""
    hl = HALF_LIFE_DAYS.get(kind, 90.0)
    return math.pow(0.5, age_days / max(1.0, float(hl)))


class MemoryGraph:
    """Graph API on top of a Store."""

    def __init__(self, store: Store):
        self.store = store

    # ---------------- graphdb (neuron/synapse) operations ------------------
    def add_neuron(self, kind, content, source="local", ts=None, confidence=0.5,
                   meta=None) -> str:
        """Create a neuron. Returns its id (synapse endpoints use these)."""
        node_id = uuid.uuid4().hex[:12]
        self.store.add_node(node_id, kind, str(content), source or "local", ts,
                            confidence, {
                                "title": (meta or {}).get("title", str(content)[:64]),
                                **(meta or {}),
                            })
        return node_id

    def add_synapse(self, src, dst, rel="related_to", weight=1.0, ts=None) -> None:
        """Connect two neurons with a typed synapse."""
        self.store.add_edge(src, dst, rel, weight, ts)

    def delete_neuron(self, node_id) -> None:
        """Right to forget: cascade-deletes all synapses of the neuron."""
        self.store.delete_node(node_id)

    def stats(self) -> dict:
        by_kind = self.store.count_by_kind()
        return {
            "neurons": self.store.count_nodes(),
            "synapses": len(self.store.all_edges()),
            "by_kind": by_kind,
        }

    def neuron(self, node_id):
        row = self.store.get_node(node_id)
        return self._row_dict(row) if row else None

    def _row_dict(self, row):
        d = dict(row)
        try:
            d["meta"] = row["meta"] and json_loads_meta(row["meta"])
        except Exception:
            d["meta"] = {}
        return d

    # ---------------- recall ------------------------------------------------
    def recall(self, query, k=5, identity=True, threshold=0.02):
        """Identity-grounded, evidence-validity-ranked memory retrieval.

        score = cosine(query, neuron) * decay(kind) * identity_grounding * evid_validity
        """
        q = tokenize(query)
        if not q:
            return []
        qtf = _tf(q)
        nodes = self.store.all_nodes()

        # ID-RAG identity closure: nodes that ARE identity or touch identity nodes.
        identity_set = {r["node_id"] for r in nodes if r["kind"] in IDENTITY_KINDS}
        if identity and identity_set:
            adj = set()
            for e in self.store.all_edges():
                if e["src"] in identity_set:
                    adj.add(e["dst"])
                if e["dst"] in identity_set:
                    adj.add(e["src"])
        else:
            adj = set()

        scored = []
        for row in nodes:
            content = row["content"] or ""
            ntoks = tokenize(content)
            ntf = _tf(ntoks)
            dot = sum(qtf.get(t, 0.0) * ntf.get(t, 0.0) for t in qtf)
            nq = _norm(qtf)
            nn = _norm(ntf)
            base = dot / (nq * nn + 1e-9) if nq and nn else 0.0
            if base <= 0:
                continue
            d = decay(_age_days(row["ts"]), row["kind"])
            # ID-RAG: boost neurons grounded in the identity knowledge structure.
            g = 1.0
            if identity:
                if row["node_id"] in identity_set:
                    g = 1.6
                elif row["node_id"] in adj:
                    g = 1.35
            # PGMem: persona-level signals are only as good as their evidence.
            ev = self._evidential_validity(row["node_id"], row["kind"], ntoks)
            s = base * d * g * ev
            if s >= threshold:
                scored.append((s, {
                    "id": row["node_id"],
                    "kind": row["kind"],
                    "content": content,
                    "source": row["source"],
                    "ts": row["ts"],
                    "confidence": row["confidence"],
                    "score": round(s, 4),
                    "cosine": round(base, 4),
                    "decay": round(d, 4),
                    "grounding": round(g, 4),
                    "evidence": round(ev, 4),
                }))
        scored.sort(key=lambda x: -x[0])
        return [s for _, s in scored[:k]]

    def _evidential_validity(self, node_id, kind, ntoks) -> float:
        """PGMem: a persona-level signal is weighted by how many evidence
        synapses support it. Event-level neurons keep full fidelity."""
        if kind not in ("persona_signal", "value", "trait", "preference"):
            return 1.0
        n = 0
        try:
            for e in self.store.edges_for(node_id):
                if e["rel"] in ("evidence_for", "supports", "source_of"):
                    n += 1
        except Exception:
            pass
        if n == 0:
            return 0.3  # unsupported persona signal: heavily discounted
        return min(1.5, 0.5 + 0.25 * n)

    # ---------------- contradictions / truth signal ------------------------
    def contradictions(self):
        """Pairs of neurons that formally contradict."""
        out = []
        for e in self.store.contradiction_edges():
            a = self.store.get_node(e["src"])
            b = self.store.get_node(e["dst"])
            if a and b:
                out.append({
                    "a": self._row_dict(a),
                    "b": self._row_dict(b),
                    "rel": "contradicts",
                    "weight": e["weight"],
                })
        return out

    def contradiction_ratio(self) -> float:
        total_pairs = 0
        contrad = len(self.store.contradiction_edges())
        try:
            prefs = [n for n in self.store.all_nodes() if n["kind"] == "preference"]
            topics = {}
            for p in prefs:
                meta = json_loads_meta(p["meta"])
                t = meta.get("topic", _topic_of(p["content"]))
                topics.setdefault(t, []).append(p)
            for t, ps in topics.items():
                if len(ps) >= 2:
                    total_pairs += len(ps) * (len(ps) - 1) // 2
        except Exception:
            pass
        denom = max(1, total_pairs + contrad)
        return contrad / denom

    # ---------------- timeline / export -------------------------------------
    def timeline(self, limit=100):
        rows = self.store.all_nodes()
        rows = sorted(rows, key=lambda r: r["ts"] or "", reverse=True)
        return [self._row_dict(r) for r in rows[:limit]]

    def graph_export(self, cytoscape=True):
        """Export the graphdb to JSON. Cytoscape format by default (compatible
        with the OI/Neural Research OS neuron graph and standard graph tools)."""
        neurons = []
        for r in self.store.all_nodes():
            neurons.append({
                "data": {
                    "id": r["node_id"],
                    "label": json_loads_meta(r["meta"]).get("title", r["content"][:64]),
                    "kind": r["kind"],
                    "content": r["content"],
                    "source": r["source"],
                    "confidence": r["confidence"],
                }
            })
        synapses = []
        for e in self.store.all_edges():
            synapses.append({"data": {"source": e["src"], "target": e["dst"], "label": e["rel"], "weight": e["weight"]}})
        if cytoscape:
            return {"elements": {"neurons": neurons, "synapses": synapses}}
        return {"neurons": [n["data"] for n in neurons],
                "synapses": [s["data"] for s in synapses]}


def _tf(tokens):
    tf = {}
    for t in tokens:
        tf[t] = tf.get(t, 0.0) + 1.0
    return tf


def _norm(tf):
    return math.sqrt(sum(v * v for v in tf.values()))


def _topic_of(content):
    toks = tokenize(content)
    return " ".join(toks[:6]) if toks else "unknown"


def json_loads_meta(raw):
    import json
    if not raw:
        return {}
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return {}
    return dict(raw) or {}