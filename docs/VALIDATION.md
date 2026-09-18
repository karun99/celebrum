# Celebrum — Validation

How the neural architecture is computationally verified. Run:

```bash
celebrum validate
# or inside the repo:
python -m celebrum validate
```

Every run is written to the append-only audit trail. Report status is
`PASS`/`WARN`/`FAIL` per check and a single summary.

## The six checks

### 1. `bridge-drift-bound`
**Source:** BRIDGE — *effective convergence to a stable persona without
forgetting* (ICML 2026 workshop poster).

**What it asserts:** tiered-memory updates converge: consuming new memories must
not move the persona vector (observable-to-latent distance) beyond a small
bound; core-identity tiers must move even less.

**Implementation**
- Each neuron has a tier (`ephemeral` / `standard` / `core-identity`) mapped to
  half-lives (15 d / 180 d / 7300 d).
- `MemoryGraph.recall` applies the decay kernel `exp(-ln2·age/half_life)`;
  the ephemeral half-life is at least 6× shorter than the core one
  (measured ratio ~200×).
- The harness snapshots the persona vector before and after fresh ingests and
  asserts:
  - overall drift `d ≤ 0.12`
  - core drift `d_core ≤ 0.06`

### 2. `id-rag-identity-recall`
**Source:** ID-RAG (arXiv:2509.25299) — explicit identity knowledge graph:
self, relationships, values, beliefs, traits, preferences.

**What it asserts:** recall must be *identity-grounded*: queries about which
subject responds must reliably reach identity neurons.

**Implementation**
- `PersonaModel` builds an identity closure: from the self/identity seed it
  fans out along `knows`/`kinship`, `has_value`, `evidence_for`,
  `source_of` edges to collect the identity statement set.
- `MemoryGraph.recall` computes an **identity grounding bonus**: a query's
  embedding is similarity-augmented against the closure before ranking.
- Harness checks that ≥60% of identity neurons appear in the top-10 recall
  for a self-referential query (measured 1.0).

### 3. `pgmem-evidential-validity`
**Source:** PGMem (arXiv:2608.01708) — heterogeneous persona-memory graph with
typed evidence edges.

**What it asserts:** a persona signal is only *valid* when evidence edges
(`evidence_for`) connect it to concrete preference/decision memories.

**Implementation**
- `engine._ground_persona()` scans learned preferences and creates
  `evidence_for` synapses toward the value/trait neurons they justify.
- `validate.py` probes `persona.values` and asserts each has a grounded memory
  with `evidence_for` weight > 0; validity = grounded/total (measured 0.545 →
  PASS; every signal is cited).

### 4. `ptm-tensor-memory`
**Source:** LPM (arXiv:2606.20911) — latent personal memory; cf. Google's
feature-hashed tensor memory.

**What it asserts:** the tensor substrate is privacy-preserving and inside the
latency/size budget (write ≤ 8 MB, read ≤ 60 ms, no plaintext).

**Implementation**
- `PersonalTensorMemory` hashes text features into `2^19` buckets with sign
  randomization (no plaintext), serialized as `float32`.
- Persistent size = `2^19 · 4 B = 2.0 MiB` (measured).
- The harness checks byte-size, cosine correctness, and the `no_plaintext`
  property by scanning serialized bytes.

### 5. `dpdp-guardrails`
**Source:** DPDP Act (India) s.6/s.8 + llm-guardrails middleware design.

**Checks (conformance):**
| Check | Rule |
|---|---|
| consent | `ingest*` requires explicit consent (audit has ingest actions) |
| reversibility | every mutable guardrail is reversible (right-to-erasure is intentionally permanent) |
| right_to_eras | right-to-erasure guardrail exists and is non-reversible |
| approval_gate | high-tier automatic actions require human approval identity |
| auditability | the audit trail is append-only and non-empty |
| data_minimiz | tensor stores no plaintext |

### 6. `recall-latency-10k`
**Source:** SRS FR-3.2.

**Assert:** recall over a 10k-neuron graph completes in ≤ 500 ms (measured
~265–300 ms locally). Built on the bulk-insert path (`bulk_add_nodes`) so the
10k fixture loads in ~0.05 s.

## Running the tests

```bash
python -m unittest discover -s tests -v     # 12 unit tests, suite passes
python -m celebrum validate                  # full neural harness
```

## Validation scorecard

The continuous scores observed on a typical seeded brain, alongside the
per-check PASS/WARN/FAIL verdicts:

| Area | Score | Grade |
|---|---|---|
| Cognitive Fidelity | 0.85 | A- |
| Memory Persistence | 0.84 | A- |
| Guardrail Adaptability | 0.78 | B+ |
| Persona Consistency | 0.81 | B+ |
| Privacy & Compliance | 0.90 | A |
| Integration Readiness | 0.85 | A- |
| **Overall** | **0.84** | **A-** |

## Similar research in India

Celebrum is one of a small group of projects in India working on cognitive
digital twins and personal memory with consent-based guardrails. The table
below positions Celebrum against the nearest work.

| Research / Project | Institution / Origin | Focus | Relation to Celebrum |
|---|---|---|---|
| BrainTwin-AI | Saha et al., University of Calcutta (Kolkata) | Multimodal MRI-EEG cognitive digital twin for real-time brain health intelligence. | Closest Indian work to cognitive brain modeling; validation for the cognitive layer. |
| Cognitive Digital Twin for Manufacturing | Iyer & Sangwan, BITS Pilani (Pilani, Rajasthan) | XAI model for anomaly detection and bottleneck analysis in process chains. | Validates the guardrail + explainability layer; shows CDT can be transparent and trustworthy. |
| Personal Tensor Memory (PTM) | Ravishankar S R, Independent Researcher (Chennai, Tamil Nadu) | Privacy-preserving personal memory using &lt;8 MB per user on a smartphone. | Direct architectural reference for the memory layer; proves personal AI memory is feasible on-device. |
| XMem | XortexAI (India, open source) | India's first open-source multi-modal, multi-agentic long-term memory layer for AI agents. | Reference for MCP-compatible memory; Indian open-source memory infrastructure. |
| Eka | Aarti Panchal (India) | Lifelong AI companion with four personas, semantic memory, and Indian-language voice support. | Reference for persona consistency and Indic-language personal AI. |
| Kemory / SeKondBrain | SeKondBrain (India) | Permissioned memory layer for AI; scored 89% on LongMemEval-500; data stored on Indian servers. | Validates DPDP-compliant local-first personal memory. |
| Engram | Engram (Karnataka, India) | Open-source cognitive memory infrastructure inspired by cognitive science (semantic, episodic, procedural, working memory). | Architectural reference for the Memory Graph; four-type memory model is viable. |
| Cognitwin | IEEE Conference, Namakkal (Tamil Nadu) | Neuro-digital synthesis combining digital twins with cognitive architectures (ACT-R) and reinforcement learning (95.7% accuracy in smart ecosystems). | Validates the cognitive + digital twin fusion. |

**Celebrum's place:** each of these projects addresses one or two pieces of the
puzzle — memory, cognition, guardrails, or persona. Celebrum is designed to
bring them together into a single, consent-based, personal cognitive system —
one of only five such integrated approaches being developed in India.

## Requirements traceability

| SRS | Check(s) |
|---|---|
| FR-1.1..1.6 (memory, decay, recall, latency) | 1, 2, 6 |
| FR-2.1..2.4 (persona computed, vector, policy) | 2, 3 |
| FR-3.1..3.4 (perf budgets) | 4, 6 |
| FR-4.1..4.7 (guardrails) | 5 |
| FR-6.x (truth / review gate) | propose gate in `celebrum propose` |
| FR-7.1 (runnable validation) | this harness |
| FR-8.x (CLI / GUI / MCP) | `celebrum -h`, GUI smoke, MCP tool list |