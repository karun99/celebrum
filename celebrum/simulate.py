"""Simulation (FR-6) - 'what if' scenario engine.

Runs the Persona Model + Memory Graph over a hypothetical scenario and returns:
  * a stance (agree / neutral / oppose) derived from value alignment,
  * the reasoning trail (recalled neurons + decision heuristics),
  * a response sketch shaped by the persona's style vector,
  * any value conflicts (FR-6.2).

No LLM is invoked; everything is a transparent, on-device approximation of
thought - exactly what Celebrum is for.
"""

from __future__ import annotations

from .memory import MemoryGraph, tokenize
from .persona import PersonaModel

# metaphorical value-opposition lexicon for conflict detection
CONFLICT_LEXICON = {
    "privacy": ["share", "public", "publish", "leak", "expose", "third-party", "cloud"],
    "honesty": ["cheat", "lie", "fake", "deceive", "mislead", "plagiarize"],
    "safety": ["risky", "danger", "unsafe", "exploit", "attack", "harm"],
    "freedom": ["restrict", "censor", "force", "lock-in", "block"],
    "family": ["abandon", "alone", "ignore", "neglect"],
    "commitment": ["quit", "give_up", "skip", "procrastinate"],
    "truth": ["mislead", "unverified", "rumor", "fake", "lie"],
}


class Simulation:
    def __init__(self, persona: PersonaModel, graph: MemoryGraph):
        self.persona = persona
        self.graph = graph

    def run(self, scenario: str) -> dict:
        toks = tokenize(scenario)
        recalled = self.graph.recall(scenario, k=5)
        values = sorted(self.persona.values, key=lambda v: -float(v.get("strength", 0.0)))

        # stance via value alignment
        stance_score = 0.0
        value_hits = []
        for v in values[:5]:
            key_toks = set(tokenize(v.get("key", "")))
            overlap = len(key_toks & set(toks))
            # positive phrasing: value alignment pushes toward agreement
            weight = float(v.get("strength", 0.5)) * 0.5
            stance_score += weight * (1 if overlap else -0.1)
            if overlap:
                value_hits.append({"value": v.get("label"), "overlap": overlap, "strength": round(weight, 3)})
        if stance_score >= 0.1:
            stance = "agree"
        elif stance_score <= -0.15:
            stance = "oppose"
        else:
            stance = "neutral"

        # conflict detection
        conflicts = []
        joined = " ".join(toks)
        for aka, triggers in CONFLICT_LEXICON.items():
            if any(t in joined for t in triggers):
                conflicts.append({"value": aka, "trigger": next(t for t in triggers if t in joined),
                                  "severity": "high" if aka in ("safety", "privacy", "truth", "honesty") else "medium"})

        # decision heuristics
        reasoning = []
        for h in self.persona.heuristics[:4]:
            trig = set(tokenize(h.get("trigger", ""))[:6])
            if trig & set(toks):
                reasoning.append({"heuristic": h.get("rule", ""), "trigger": h.get("trigger", "")})
        reasoning += [{"memory": r["content"], "kind": r["kind"], "score": r["score"]} for r in recalled[:3]]

        style = self.persona.style
        reply = self._draft(stance, scenario, style)

        return {
            "scenario": scenario,
            "stance": stance,
            "stance_score": round(stance_score, 3),
            "value_hits": value_hits,
            "value_conflicts": conflicts,
            "reasoning": reasoning,
            "recalled": recalled,
            "response_draft": reply,
            "style_applied": style,
        }

    def _draft(self, stance, scenario, style):
        formality = float(style.get("formality", 0.5))
        warmth = float(style.get("warmth", 0.6))
        humor = float(style.get("humor", 0.4))
        prefix = "I would" if formality > 0.6 else ("Hmm, I'd" if humor > 0.5 else "I'd")
        close = "Regards." if formality > 0.7 else ("That's how I see it." if warmth > 0.6 else "That's my take.")
        action = "support this" if stance == "agree" else ("push back on this" if stance == "oppose" else "weigh this carefully")
        return f"{prefix} {action} - scenario: {scenario[:120]}... {close}"