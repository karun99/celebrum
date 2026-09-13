"""Persona Model - the probabilistic approximation of a user's thought process.

Learned from the Memory Graph (PGMem-style: values that appear in many
preferences and are reinforced by decisions become stronger) and projected into
a fixed vector for drift measurement (BRIDGE).

Schema follows SRS 5.1: id, style, heuristics, values, tone, knowledge_domains,
last_updated, version.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from .memory import MemoryGraph, tokenize, json_loads_meta


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# Canonical style dimensions (0..1).
STYLE_KEYS = ["formality", "warmth", "humor", "verbosity"]
TONE_KEYS = ["pos", "neu", "neg"]

# Deterministic feature order for velocity/drift vector.
DRIFT_FEATURES = STYLE_KEYS + TONE_KEYS + ["value_mean", "domain_count", "heuristic_count"]


class PersonaModel:
    """A lightweight, interpretable persona. Pure data + small aggregations."""

    def __init__(self, persona_id="default", style=None, heuristics=None, values=None,
                 tone=None, knowledge_domains=None, last_updated=None, version=1):
        self.id = persona_id
        self.style = dict(style or {"formality": 0.5, "warmth": 0.6,
                                    "humor": 0.4, "verbosity": 0.5})
        self.heuristics = list(heuristics or [])
        self.values = list(values or [])
        self.tone = dict(tone or {"pos": 0.5, "neu": 0.3, "neg": 0.2})
        self.knowledge_domains = list(knowledge_domains or [])
        self.last_updated = last_updated or _now()
        self.version = int(version)

    # ---------------- serialization ---------------------------------------
    def to_dict(self):
        return {
            "id": self.id,
            "style": self.style,
            "heuristics": self.heuristics,
            "values": self.values,
            "tone": self.tone,
            "knowledge_domains": self.knowledge_domains,
            "last_updated": self.last_updated,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            persona_id=d.get("id", "default"),
            style=d.get("style"),
            heuristics=d.get("heuristics"),
            values=d.get("values"),
            tone=d.get("tone"),
            knowledge_domains=d.get("knowledge_domains"),
            last_updated=d.get("last_updated"),
            version=d.get("version", 1),
        )

    # ---------------- learning (PGMem-style aggregation) -------------------
    def build(self, graph: MemoryGraph) -> "PersonaModel":
        """Aggregate the Memory Graph into style/values/heuristics/tone."""
        nodes = graph.store.all_nodes()
        value_lift = {}
        value_evidence = {}
        tone = {"pos": 0.0, "neu": 0.0, "neg": 0.0}
        domains = {}
        decision_rules = []

        for r in nodes:
            kind = r["kind"]
            content = r["content"] or ""
            conf = r["confidence"] or 0.5
            meta = json_loads_meta(r["meta"])

            if kind == "preference":
                sentiment = float(meta.get("sentiment", 1.0 if _affirms(content) else -1.0))
                topic = meta.get("topic") or " ".join(tokenize(content)[:6])
                if sentiment > 0:
                    tone["pos"] += conf
                    value_lift[topic] = value_lift.get(topic, 0.0) + conf
                elif sentiment < 0:
                    tone["neg"] += conf
                    value_lift["avoid_" + topic] = value_lift.get("avoid_" + topic, 0.0) + conf
                else:
                    tone["neu"] += conf
                value_evidence[topic] = value_evidence.get(topic, 0) + 1

            elif kind == "decision":
                ctx = meta.get("context", content)
                choice = meta.get("choice", "")
                rule = meta.get("rationale", "")
                decision_rules.append({
                    "trigger": " ".join(tokenize(ctx)[:16]),
                    "rule": (choice or content)[:160],
                    "confidence": conf,
                    "evidence": rule[:120],
                })

            elif kind in ("milestone", "note", "fact"):
                toks = tokenize(content)
                for t in toks[:12]:
                    domains[t] = domains.get(t, 0.0) + conf

        # normalize tone
        tot = sum(tone.values()) or 1.0
        tone = {k: round(v / tot, 3) for k, v in tone.items()}
        for k in TONE_KEYS:
            tone.setdefault(k, 0.0)

        values = []
        for topic, lift in sorted(value_lift.items(), key=lambda x: -x[1]):
            values.append({
                "key": topic[:48],
                "label": topic[:48],
                "strength": round(min(1.0, lift / max(1.0, len(nodes) ** 0.5)), 3),
                "evidence": value_evidence.get(topic, 1),
            })

        domains_sorted = [d for d, _ in sorted(domains.items(), key=lambda x: -x[1])[:12]]
        style_meta = json_loads_meta({} if not nodes else {})
        # keep prior style, only nudge warmth by positive tone
        self.style["warmth"] = round(0.5 + tone["pos"] * 0.5, 3)
        self.values = values[:12] or self.values
        self.tone = tone
        self.knowledge_domains = domains_sorted or self.knowledge_domains
        if decision_rules:
            self.heuristics = decision_rules[:12] or self.heuristics
        self.last_updated = _now()
        self.version += 1
        return self

    # ---------------- drift vector ----------------------------------------
    def to_vector(self):
        """Fixed-length vector used by the BRIDGE drift bound."""
        v = []
        for k in STYLE_KEYS:
            v.append(float(self.style.get(k, 0.5)))
        for k in TONE_KEYS:
            v.append(float(self.tone.get(k, 0.3)))
        v.append(sum(v.get("strength", 0.0) for v in self.values) / max(1, len(self.values)))
        v.append(min(1.0, len(self.knowledge_domains) / 12.0))
        v.append(min(1.0, len(self.heuristics) / 12.0))
        return v

    # ---------------- feedback ---------------------------------------------
    def apply_feedback(self, dimension, delta) -> None:
        """FR-3.5: update model via user feedback."""
        if dimension in STYLE_KEYS:
            cur = float(self.style.get(dimension, 0.5))
            self.style[dimension] = max(0.0, min(1.0, cur + float(delta)))
        elif dimension in TONE_KEYS:
            cur = float(self.tone.get(dimension, 0.2))
            self.tone[dimension] = max(0.0, cur + float(delta) * 0.1)
        self.last_updated = _now()
        self.version += 1


def _affirms(content):
    import re
    neg = re.search(r"\b(dislike|hate|avoid|not|no|reject|against)\b", content.lower())
    return neg is None