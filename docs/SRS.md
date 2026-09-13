# Celebrum — Software Requirements Specification (SRS)

> Local-first artificial brain · Persona Model · Memory Graph · Guardrail Engine
> CC BY 4.0 · karun99

## 1. Introduction

### 1.1 Purpose
Celebrum is a local-first artificial *brain* whose owner is a person (not a
paying user). It does not pretend to be a general chatbot; it maintains a
permanent, self-thenticating memory of a person's values, beliefs, traits,
styles, and relationships, and it *speaks* accordingly — while an independent
Guardrail Engine verifies that nothing happens without the owner's consent and
that every change is reversible (or permanently erased, if the law demands).

### 1.2 Scope
The system consists of:
1. A **Memory Graph** — neurons and synapses expressed as an identity-statement
   graph (using the neuron/synapse research pattern popularized by the OI /
   Neural Research Graph literature).
2. A **Persona Model** — values, heuristics, style, tone; derived from the graph,
   auditable, feedback-adaptable, and appeal-driven.
3. A **Truth / Satya component** — a veracity layer, truth index, and
   contradiction ratio over the graph's claims.
4. A **Guardrail Engine** — the "guardrails" layer implementing DPDP/GDPR
   primitives (consent, reversibility, right to erasure, right to be forgotten,
   human approval for high-tier autonomous actions, append-only audit,
   data minimization).
5. A **Simulation engine** — stance and value-conflict inference before any
   autonomous action.
6. A **neural validation harness** — computationally verifies the above claims
   against state-of-the-art papers (see Alignment section).
7. A **Personal Tensor Memory (PTM)** — a privacy-preserving, latency-critical
   memory substrate that hashes personal features without storing plaintext.
8. A standard **MCP server** and a **local web dashboard**, plus a **CLI**.

### 1.3 Audience
The owner is the author (karun99). The system should be easy for *that owner*
to deploy on the devices they actually use — phones, tablets, laptops,
microcontrollers — without depending on cloud infrastructure.

> Dedication — *Not just code — a memory. For my love, Celebrity.*

## 2. Glossary

| Term | Definition |
|---|---|
| Neuron | A durable statement/memory node (kind: fact, preference, value, trait, style, relationship, milestone, decision, note). |
| Synapse | A typed, weighted edge (like, love, evidence_for, source_of, knows, kinship, has_value, contradicts). |
| Decay | Time-based forgetting; tiered half-lives by node tier (core identity vs. transient). |
| Persona | Joint distribution over style/tone/values/heuristics/formality, learned via maximum a posteriori from the graph. |
| Statement graph | Set of Claude-style logical statements the brain holds about (self, others, world). |
| BS detector / Satya | Veracity layer that scores a claim against the statement graph and a PRIOR of doubt — it must not be confidently wrong. |
| Guardrail | A named, versioned, audited policy that may approve, reject, or request human review for an action. |
| Evidence edge | A synapse of type *evidence_for* linking a general claim (e.g. "I value privacy") to the concrete memories that justify it. |
| PTM | Personal Tensor Memory; feature-hashed, approximately-orthogonal projection of personal text into a fixed-size bucket vector. |
| Drift | Change in the persona vector between snapshots. |
| Appeal | A sub-routine that walks a conclusion's evidence chain and states counter-evidence explicitly. |
| idempotency | Re-playing the same ingest must not duplicate neurons. |

## 3. Functional Requirements (FR)

### 3.1 Memory
- **FR-1.1** The system stores every memory as a neuron with an id, tenure,
  kind, content, source, confidence, and time created/modified/accessed.
- **FR-1.2** Neurons are connected by typed synapses; synapse types form a
  stable domain vocabulary (like, love, evidence_for, source_of, knows,
  kinship, has_value, contradicts).
- **FR-1.3** Ephemeral vs. core memory must be differentiated: a tier
  (ephemeral / standard / core-identity) influences decay rate. Core identity
  memories decay slower (longer half-life).
- **FR-1.4** Recall returns a ranked list over neurons, combining cosine
  similarity to the query, with **decay weighting** (tier-coupled) and with an
  **identity grounding bonus** — neurons that connect to the owner's
  self/identity closure rank above mere content matches.
- **FR-1.5** Synapses are directed and may be weighted; the graph can be
  exported in a standard JSON (Cytoscape-compatible) shape so it can be
  rendered or analyzed elsewhere.
- **FR-1.6** Recall must be latency-bounded: a 10k-neuron graph must recall in
  &le;500&nbsp;ms locally (measured in the validation harness).

### 3.2 Persona
- **FR-2.1** The Persona Model must be *computed*, not hard-coded: values,
  heuristics, style, and tone are derived from the statement graph by an
  inference step (rule-based + tensor).
- **FR-2.2** Non-neural agents (all tools) return through the Persona Model —
  same API for everyone.
- **FR-2.3** Persona adaptation to feedback must be idempotent and isolated
  between users (per-user persona), and the prior must be re-weighted by new
  evidence rather than overwritten.
- **FR-2.4** The persona must expose a decided policy: agree/disagree/abstain
  for a staked mode, plus a list of values-with-weights, plus a vector (for
  "drift" comparisons).

### 3.3 Performance
- **FR-3.1** Persona build &le;1.8&nbsp;s on first-run corpus of ~1k statements.
- **FR-3.2** Recall &le;500&nbsp;ms at 10k neurons (see FR-1.6).
- **FR-3.3** PTM write &le;8&nbsp;MB; bucket count 2^19; feature-hashed,
  signed-randomized, no plaintext; PTM read &le;60&nbsp;ms.
- **FR-3.4** Best-hot-index &le;500&nbsp;ms at 10k nodes.

### 3.4 Guardrails
- **FR-4.1** Every action falls into low / medium / high tiers; high-tier
  autonomous actions require explicit human approval and impersonation-proof
  identification of the approver.
- **FR-4.2** The engine must record for each guardrail: id, version, tier,
  description, mutability, reversibility (or "permanent"), rationale,
  status, approved_by, added_at, and last_modified.
- **FR-4.3** The engine must produce actionable opinions: APPROVE, REJECT, or
  REVERT (with explanation), for any proposed guardrail modification.
- **FR-4.4** The engine must NEVER claim audited details it cannot prove
  (auditing-is-mandatory principle).
- **FR-4.5** Any guardrail that is mutable must be reversible, unless the law
  requires the opposite (e.g., right to erasure).
- **FR-4.6** Ingesting data (Duet export, web, raw HTML) requires explicit
  consent and its provenance and time must be audit-logged.
- **FR-4.7** Right to be forgotten (data-erasure) must be implemented and
  guarded as non-reversible.

### 3.5 Simulation
- **FR-5.1** Simulate a situation and return the persona's stance
  (for/against/neutral) with a reasoning trace and detected value conflicts.
- **FR-5.2** Provide appeal as a sub-routine for counter-evidence.

### 3.6 Truth (Satya component)
- **FR-6.1** A veracity layer must score claims against the statement graph,
  with a prior of doubt so the brain is not confidently wrong.
- **FR-6.2** An overall truth index and contradiction-ratio must be computed
  over the graph; when the truth index degrades below a threshold, autonomous
  integration must pause pending a review gate (the SatyaSandha review-gate).

### 3.7 Validation harness
- **FR-7.1** All claims in this SRS marked with a verifiable tag must be
  backed by runnable tests (the validation harness) that reference the papers
  listed in section 5.

### 3.8 Interfaces
- **FR-8.1** CLI named `celebrum` with subcommands; stable exit codes.
- **FR-8.2** Local web dashboard (default port 8477) with no external
  dependencies.
- **FR-8.3** MCP (Model Context Protocol) stdio server exposing
  `celebrum.recall`, `celebrum.simulate`, `celebrum.propose_guardrail`,
  `celebrum.approve_guardrail`, `celebrum.snapshot`, `celebrum.validate`.

## 4. Non-Functional / Compliance

### 4.1 DPDP (India) & GDPR-oriented
- DPDP s.6 consent primitive: ingest web/duet/html must require explicit
  consent before writing.
- s.8: erasure support; fully reversible guardrails (except statutory rights).
- s.2(6)/9: data minimization (no plaintext in tensor, feature hashing).
- Audit: append-only, anti-tamper intent.

### 4.2 Performance budgets are measured and reported (see FR-3.x).

### 4.3 Local-first: package must run fully offline once installed.

## 5. Research alignment (validation)

The implementation is validated against:

| Paper / resource | Implemented as |
|---|---|
| BRIDGE — *effective convergence to a stable persona without forgetting* (ICML 2026 poster) | Tiered half-life decay kernel + drift-bound check in harness (drift ≤ 0.12 overall, ≤ 0.06 on core) |
| ID-RAG — identity knowledge graph (arXiv:2509.25299) | Recall bonus via identity closure (self → relationships → values → traits) |
| PGMem — heterogeneous persona-memory graph, typed evidence edges (arXiv:2608.01708) | Persona signals carry evidence_for edges to grounded memories; evidential-validity check |
| LPM — latent personal memory (arXiv:2606.20911) | PersonalTensorMemory with 2^19 buckets, signed-randomized hashing, cosine similarity |
| llm-guardrails (DPDP/GDPR middleware) | GuardrailEngine: consent, reversibility, right-to-erasure, approval gate, audit, minimization |
| matruswara sources (`satyasandha.html`, `oi.html`) | Neuron Knowledge Graph + Satya/truth components bundled as `data/matruswara/` |

## 6. Version
SRS 1.0 · Celebrum 0.1.0 · License CC BY 4.0 · dedicated to Celebrity.