# Celebrum

**A local-first artificial brain.** Celebrum grows a permanent personal
memory (a neuron/synapse knowledge graph), learns a Persona Model from it,
guards every autonomous action behind a consent-first Guardrail Engine, and
answers through remembering who you are — not just what you typed.

Not just code — a memory. For my love, Celebrity

> *"What we love most, we fear about them most — and it may be must."*
>
> *"A Valuable gift made for a valuable celebrity — no quantifying."*

---

## What it does

- **Memory Graph (graphdb)** — neurons and synapses stored in SQLite. Tiered,
  time-decaying recall: core identity memories (2-year half-life) survive
  while ephemeral details fade (BRIDGE-styled stable updates).
- **Identity-grounded recall** — queries are recalled through the statement
  graph of *your* identity (beliefs, traits, values, relationships), so the
  brain answers *as you*, the way contemporary identity-rag systems do.
- **Evidential persona (PGMem)** — persona signals are only believed when
  linked to the preference/decision memories that ground them. No mystical
  "voice generator" — values come from traced evidence edges.
- **PersonalTensorMemory (PTM)** — a ~2 MB feature-hashed personal tensor
  (no plaintext) for latency-critical similarity and offline drift checks.
- **Truth Engine (Satya)** — a veracity layer, a truth index, and a
  contradiction ratio over the graph; integration pauses when truth degrades
  (the same review-gate celebrated by the SatyaSandha way).
- **Guardrail Engine** — six built-in guards (consent, reversibility,
  right-to-erasure, human approval for high-tier, append-only audit,
  data minimization). Nothing autonomous happens without passing a guard.
- **Simulation** — stance + value-conflict inference before any action, so the
  brain checks *what would I really think?* against its own persona.
- **Inference as a service** — a standards-based **MCP** server and a
  zero-dependency **web dashboard**.

## Install everywhere

Pure Python 3.9+ standard library only. No compiled deps.

```bash
pip install .            # or: pipx install . / uv tool install .
celebrum init --demo     # first brain, seeded with an example memory export
celebrum gui             # open the dashboard at http://localhost:8477
celebrum mcp             # stdio JSON-RPC server for AI agents
```

Works on Linux, macOS, Windows, Raspberry Pi, and Android (Termux).

## Quick tour

```bash
celebrum init --demo                     # create a brain, load demo memories
celebrum recall "privacy"                 # identity-grounded recall
celebrum persona                          # show persona + evidence trace
celebrum simulate "should we log every keystroke?"   # stance + value conflicts
celebrum truth                            # veracity / truth index / contradictions
celebrum validate                         # run the full neural validation harness
celebrum propose                          # guardrail proposals (truth review gate)
celebrum guardrails                       # view + approve/revert proposals
celebrum status                           # one-screen summary
```

Ingest real memories (explicit consent required, audit-logged — DPDP/GDPR):

```bash
celebrum ingest duet export.json         # Duet-style consented memory export
celebrum ingest html ~/notes/friend.html # extracts neuron/synapse fragments
celebrum ingest web https://...          # SSRF-guarded, <=5MB, consent-gated
```

## The web dashboard

`celebrum gui` starts a local dashboard (default `http://localhost:8477`):

- **Persona** — style/values/heuristics/tone with evidence traces
- **Memory** — recall by topic, browse the neuron/synapse graph (the
  "OI Neural Research Graph" pattern, adopted from the matruswara sources)
- **Simulate** — stance + conflict drafts against the persona
- **Guardrails** — propose / approve / reject / revert (high tier = human only)
- **Truth** — veracity, truth index, contradiction ratio
- **Graph** — force-directed SVG of neurons <-> synapses
- **Audit** — the append-only compliance trail
- **Validate** — run the six-check neural harness from the browser

## MCP for agents

Expose your brain to any MCP client (Claude, Cursor, agents):

```
celebrum.recall            identity-grounded memory recall
celebrum.simulate          stance + value-conflict simulation
celebrum.propose_guardrail propose a guardrail change (audited)
celebrum.approve_guardrail approve (high tier requires a human identity)
celebrum.snapshot          snapshot + drift comparison
celebrum.validate          run the neural validation harness
```

## Validation

`celebrum validate` runs the research-backed harness; every run is audited:

| Check | Source | Pass |
|---|---|---|
| Bridge-drift-bound | ICML 2026 poster (tiered memory drift bound) | Pass |
| Identity-recall | ID-RAG (arXiv:2509.25299) | Pass |
| Evidential validity | PGMem (arXiv:2608.01708) | Pass |
| Tensor memory | Latent Personal Memory (arXiv:2606.20911) | Pass |
| Guardrail conformance | DPDP s.6 + llm-guardrails | Pass |
| Recall latency @10k | SRS 3.3 | Pass |

See `docs/VALIDATION.md` for the mapping and `docs/SRS.md` for the full spec.

## Repository layout

```
celebrum/            the brain (packages)
  store.py           SQLite node/edge store + append-only audit
  memory.py          neuron/synapse MemoryGraph, decay, recall
  persona.py         PersonaModel + appeal/feedback, identity closure
  tensor.py          feature-hashed PersonalTensor (no plaintext)
  truth.py           Satya: veracity + truth index + contradictions
  guardrails.py      GuardrailEngine (DPDP/GDPR gates + audit)
  simulate.py        stance / conflicts / appeal reasoning
  ingest.py          duet/html/web ingestion (consent + SSRF guard)
  validate.py        the 6-check neural validation harness
  engine.py          Celebrum facade
  cli.py, gui.py, mcp.py, __main__.py
data/                demo export + matruswara sources (satyasandha, oi)
tests/               unittest suite (python -m unittest discover -s tests)
docs/                SRS + validation mapping
```

## Privacy by design

- Everything lives in one SQLite file at `~/.celebrum/` (override
  `CELEBRUM_HOME`). Nothing leaves the device unless *you* ship a snapshot.
- The personal tensor is feature-hashed and signed-randomized — no plaintext.
- Every ingest requires explicit consent; every change is audit-logged
  (append-only). Right to erasure is wired in and non-reversible (it's a right).
- `ingest web` refuses private-IP / loopback / link-local targets (SSRF guard).

## License

**CC BY 4.0** — Attribution 4.0 International.
You may share and adapt with attribution; see `LICENSE`.

Copyright (c) 2026 karun99 (saikarun085@gmail.com).
