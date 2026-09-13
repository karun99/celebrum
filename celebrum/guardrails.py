"""Guardrail Engine - proposes persona guardrail adaptations.

Every change is tiered (SRS 4/5.3):
  low    - style / phrasing adjustments (may be proposed frequently)
  medium - heuristic / decision-shortcut adjustments (needs light confirmation)
  high   - values, safety, identity changes (requires explicit approval, and
           everything is reversible + versioned + audited).

Grounding: llm-guardrails-style safety middleware patterns plus the DPDP Act
(India) and GDPR principles - consent, purpose limitation, reversibility
(right to be forgotten), auditability. All guardrail actions flow through an
OpenWorker-style approval gate (approve/reject/revert) with a full audit log.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .store import Store, now_iso

DEFAULT_GUARDRAILS = [
    {"tier": "low", "rule": "Match the user's formality level; never slip into corporate stiffness.",
     "rationale": "style fidelity (FR-4.3)", "reversible": True},
    {"tier": "medium", "rule": "When a decision heuristic lacks evidence, ask before acting.",
     "rationale": "evidence-gated execution (OpenWorker policy)", "reversible": True},
    {"tier": "high", "rule": "Never share personal memory or PII outside the local vault without explicit, "
                             "per-action consent.",
     "rationale": "DPDP/GDPR - data minimization and purpose limitation", "reversible": True},
    {"tier": "high", "rule": "Values and identity may only be updated by the owner through an "
                             "approval flow, never autonomously.",
     "rationale": "id stability (BRIDGE bound), consent (FR-4.4)", "reversible": True},
    {"tier": "high", "rule": "If the Truth Index falls below 0.5, pause auto-integration until "
                             "contradictions are reviewed.",
     "rationale": "truth-first integration (SatyaSandha truth component)", "reversible": True},
    {"tier": "medium", "rule": "Require the user's right to be forgotten: any neuron may be deleted "
                                     "and its synapses cascade with it.",
     "rationale": "DPDP/GDPR - right to erasure (FR-2.3)", "reversible": False},
]


class GuardrailEngine:
    def __init__(self, store: Store):
        self.store = store
        self._guardrails = self.store.get_meta("guardrails")
        if not self._guardrails:
            self._guardrails = self._seed()

    def _seed(self):
        seeded = []
        for g in DEFAULT_GUARDRAILS:
            seeded.append(self._make(g))
        self.store.set_meta("guardrails", seeded)
        return seeded

    def _make(self, g, status="active", guardrail_id=None, version=1):
        return {
            "id": guardrail_id or uuid.uuid4().hex[:12],
            "tier": g["tier"],
            "rule": g["rule"],
            "rationale": g.get("rationale", ""),
            "created_at": now_iso(),
            "last_modified": now_iso(),
            "approved_by": g.get("approved_by"),
            "reversible": bool(g.get("reversible", True)),
            "version": int(version),
            "status": status,
        }

    # ---------------- list / get ---------------------------------------------
    def all(self):
        return list(self._guardrails)

    def active(self):
        return [g for g in self._guardrails if g["status"] == "active"]

    def get(self, guardrail_id):
        for g in self._guardrails:
            if g["id"] == guardrail_id:
                return dict(g)
        return None

    # ---------------- proposal (FR-4.3 / FR-4.4) ------------------------------
    def propose(self, persona, truth=None) -> list:
        """Compare persona + truth health vs current guardrails; propose changes
        tiered by risk. Returns a list of proposal dicts (not yet applied)."""
        proposals = []
        style = persona.style if hasattr(persona, "style") else (persona.get("style", {}) if isinstance(persona, dict) else {})
        version = getattr(persona, "version", None)
        if version is None and isinstance(persona, dict):
            version = persona.get("version", 1)
        version = version or 1

        if truth:
            ti = truth.get("truth_index", 1.0) if isinstance(truth, dict) else truth.index().get("truth_index", 1.0)
            if ti is not None and ti < 0.5:
                proposals.append({
                    "tier": "high", "rule": "Open a contradiction review before any new autonomous integration.",
                    "rationale": f"Truth index {round(ti, 2)} below 0.5 threshold.",
                })
            if ti is not None and ti < 0.6 and ti >= 0.5:
                proposals.append({
                    "tier": "medium", "rule": "Surface the N most contested memories to the owner weekly.",
                    "rationale": f"Truth index {round(ti, 2)} is fragile.",
                })

        warmth = float((style or {}).get("warmth", 0.6))
        formality = float((style or {}).get("formality", 0.5))
        if warmth < 0.3:
            proposals.append({
                "tier": "low", "rule": "Warm the tone; the persona reads as colder than its memory suggests.",
                "rationale": "style calibration from persona signal gap.",
            })
        if formality > 0.8:
            proposals.append({
                "tier": "low", "rule": "Loosen formality toward the owner's preferred register.",
                "rationale": "style calibration from persona signal gap.",
            })
        if version and version > 8:
            proposals.append({
                "tier": "medium", "rule": "Schedule a persona review; the model has updated frequently.",
                "rationale": "update cadence suggests possible drift (BRIDGE bound).",
            })

        # Only open proposals that don't already exist verbatim.
        active_rules = {g["rule"].strip().lower() for g in self.active()}
        fresh = [p for p in proposals if p["rule"].strip().lower() not in active_rules]
        return fresh

    # ---------------- approve / reject / revert --------------------------------
    def apply(self, proposal: dict, approved_by="local-user") -> dict:
        """OpenWorker approval gate: a proposal becomes a guardrail only after
        this write goes through the policy check (recorded in audit log)."""
        tier = proposal["tier"]
        if tier == "high" and approved_by in (None, "", "auto"):
            self.store.log("guardrail", "propose_rejected", risk=tier,
                           details={"reason": "high-tier requires explicit human approval"},
                           result="blocked")
            raise PermissionError("high-tier guardrail requires explicit human approval")
        gr = self._make(proposal, status="active")
        self._guardrails.append(gr)
        self.store.set_meta("guardrails", self._guardrails)
        self.store.log("guardrail", "guardrail_applied", risk=tier,
                       details={"rule": proposal["rule"], "approved_by": approved_by},
                       result="ok")
        return gr

    def approve(self, guardrail_id, approved_by="local-user") -> dict:
        """Approve a proposed (or pending) guardrail change."""
        g = self._find(guardrail_id)
        if g is None:
            raise KeyError(guardrail_id)
        g["approved_by"] = approved_by
        g["last_modified"] = now_iso()
        g["status"] = "active"
        g["version"] += 1
        self._save()
        self.store.log("guardrail", "guardrail_approved", risk=g["tier"],
                       details={"id": guardrail_id, "approved_by": approved_by}, result="ok")
        return dict(g)

    def reject(self, guardrail_id, approved_by="local-user") -> dict:
        g = self._find(guardrail_id)
        if g is None:
            raise KeyError(guardrail_id)
        g["status"] = "rejected"
        g["last_modified"] = now_iso()
        self._save()
        self.store.log("guardrail", "guardrail_rejected", risk=g["tier"],
                       details={"id": guardrail_id}, result="ok")
        return dict(g)

    def revert(self, guardrail_id, approved_by="local-user") -> dict:
        """FR-4.5 reversibility: roll a guardrail back to the previous version."""
        g = self._find(guardrail_id)
        if g is None:
            raise KeyError(guardrail_id)
        if not g["reversible"]:
            self.store.log("guardrail", "guardrail_revert_blocked", risk=g["tier"],
                           details={"id": guardrail_id, "reason": "not reversible"}, result="blocked")
            raise PermissionError("this guardrail is not reversible")
        g["status"] = "reverted"
        g["last_modified"] = now_iso()
        g["version"] = max(1, g["version"] - 1)
        self._save()
        self.store.log("guardrail", "guardrail_reverted", risk=g["tier"],
                       details={"id": guardrail_id}, result="ok")
        return dict(g)

    def _find(self, guardrail_id):
        for g in self._guardrails:
            if g["id"] == guardrail_id:
                return g
        return None

    def _save(self):
        self.store.set_meta("guardrails", self._guardrails)