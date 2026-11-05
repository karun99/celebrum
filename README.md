# Celebrum

**A local-first artificial brain.** Celebrum grows a permanent personal
memory (a neuron/synapse knowledge graph), learns a Persona Model from it,
guards every autonomous action behind a consent-first Guardrail Engine, and
answers through remembering who you are — not just what you typed.
[![M8ven Score](https://m8ven.ai/badge/mcp/karun99/celebrum)](https://m8ven.ai/mcp/karun99/celebrum)
Not just code — a memory. For my love, Celebrity

> *"What we love most, we fear about them most — and it may be must."*
>
> *"A Valuable gift made for a valuable celebrity — no quantifying."*

---

> Built in 8 hours.

## Quick start

### Android / Termux (one command)

1. Install **[Termux](https://f-droid.org/packages/com.termux/)** from F-Droid.
2. Open Termux and paste:

```bash
curl -fsSL https://raw.githubusercontent.com/karun99/celebrum/main/install-termux.sh | bash
```

3. Start the app:

```bash
celebrum-app
```

The dashboard opens at `http://127.0.0.1:8477`. Install **Termux:Widget** from
F-Droid and add the widget for a one-tap home-screen button. Full guide:
[docs/TERMUX.md](docs/TERMUX.md).

### Desktop / server

```bash
pip install .            # or: pipx install . / uv tool install .
celebrum init --demo     # first brain, seeded with an example memory export
celebrum gui             # dashboard at http://localhost:8477
```

Every command, flag, and example lives in
[docs/COMMANDS.md](docs/COMMANDS.md).

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

## Install

Pure Python 3.9+ standard library only. No compiled deps. Works on Linux,
macOS, Windows, Raspberry Pi, and Android (Termux).

| Platform | Install | Start |
|---|---|---|
| Android / Termux | `curl -fsSL https://raw.githubusercontent.com/karun99/celebrum/main/install-termux.sh \| bash` | `celebrum-app` |
| Desktop / server | `pip install .` (or `pipx install .`, `uv tool install .`) | `celebrum gui` |
| Docker | `docker build -t celebrum .` | `docker run --rm -p 8477:8477 celebrum gui --host 0.0.0.0` |

**Android installer options**

```bash
./install-termux.sh --with-boot     # autostart after reboot (Termux:Boot)
./install-termux.sh --no-demo       # empty brain instead of demo memories
./install-termux.sh --no-shortcut   # skip the Termux:Widget shortcut
./install-termux.sh --port 8686     # different dashboard port
./install-termux.sh --update        # pkg update before installing
```

**Update**

```bash
# Android
celebrum-app stop
curl -fsSL https://raw.githubusercontent.com/karun99/celebrum/main/install-termux.sh | bash
celebrum-app

# Desktop (from a checkout)
git pull && pip install .
```

**Uninstall** (Android, keeps your brain)

```bash
curl -fsSL https://raw.githubusercontent.com/karun99/celebrum/main/install-termux.sh | bash -s -- --uninstall
```

## App commands

`celebrum-app` is the one-tap launcher installed by the Termux installer.

| Command | What it does |
|---|---|
| `celebrum-app` | Start the dashboard and open the browser |
| `celebrum-app stop` | Stop the background dashboard |
| `celebrum-app restart` | Restart it |
| `celebrum-app status` | Show whether it is running |
| `celebrum-app open` | Open the dashboard again |
| `celebrum-app url` | Print the dashboard URL |
| `celebrum-app logs -f` | Follow the dashboard log |
| `celebrum-app doctor` | Check the install |
| `celebrum-app version` | Print the Celebrum version |

Useful flags: `--port N`, `--host 0.0.0.0` (LAN), `--no-open`, `--no-notify`.
Run `celebrum-app --help` for the in-terminal version.

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

Full CLI reference: [docs/COMMANDS.md](docs/COMMANDS.md).

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

Expose your brain to any MCP client (Claude, Cursor, agents) over stdio:

```bash
celebrum mcp
```

```json
{
  "mcpServers": {
    "celebrum": { "command": "celebrum", "args": ["mcp"] }
  }
}
```

```
celebrum.recall            identity-grounded memory recall
celebrum.simulate          stance + value-conflict simulation
celebrum.propose_guardrail propose a guardrail change (audited)
celebrum.approve_guardrail approve (high tier requires a human identity)
celebrum.snapshot          snapshot + drift comparison
celebrum.validate          run the neural validation harness
```

## Troubleshooting

```bash
celebrum-app doctor        # Android: check launcher + brain + termux-api
celebrum-app logs -f       # follow the dashboard log
celebrum status            # brain summary
celebrum validate          # full harness (all checks should pass)
```

- Browser does not open → install **Termux:API**, or open
  `celebrum-app url` manually.
- Dashboard stops in the background → run `termux-wake-lock` and disable
  battery optimization for Termux.
- Port already in use → `celebrum-app start --port 8686`.
- Demo seeding fails → re-run the installer; data is bundled under
  `share/celebrum/data`.

More in [docs/TERMUX.md](docs/TERMUX.md) and
[docs/COMMANDS.md](docs/COMMANDS.md).

## Repository layout

```
install-termux.sh    Android/Termux installer (app + widget + boot)
scripts/termux/      celebrum-app launcher
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
docs/                SRS, TERMUX guide, command reference, validation
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

Continuous scorecard (measured on a seeded brain):

| Area | Score | Grade |
|---|---|---|
| Cognitive Fidelity | 0.85 | A- |
| Memory Persistence | 0.84 | A- |
| Guardrail Adaptability | 0.78 | B+ |
| Persona Consistency | 0.81 | B+ |
| Privacy & Compliance | 0.90 | A |
| Integration Readiness | 0.85 | A- |
| **Overall** | **0.84** | **A-** |

See `docs/VALIDATION.md` for the check mapping, the scorecard details, and the
"Similar research in India" comparison (BrainTwin-AI, BITS Pilani CDT,
PTM, XMem, Eka, Kemory/SeKondBrain, Engram, Cognitwin). See `docs/SRS.md` for
the full spec.

## Ecosystem: Zoe and Emoja

Celebrum is the **memory** substrate — one person, a governed graph of what they
told you, verified against a truth index. It is complementary to
[**Project Zoe**](https://github.com/karun99/zoe), the local-first companion
stack.

Zoe now ships **Emoja**, its consented, non-diagnostic reflection layer: a
module of Zoe, not a second project. Emoja reads only the user's own text and
returns an emoji sequence, an OKLCH-blended hex palette, a pattern in words, a
Shatkona balance check, a symbolic depth rung, and one plain sentence. Its
trust boundary is explicit — `SUNO` is the sole raw-text input, `DRISHTI` holds
an enforced veto over aesthetic output, and high distress or crisis drops the
aesthetics entirely. It is **not** therapy, emotion detection, or a diagnostic
tool, and it does not read faces, voices, biosignals, or keystrokes.

```bash
zoe emoja "I felt tired after the meeting but I am steady now"
zoe emoja --json "I feel a little sad."
```

- Emoja spec: <https://github.com/karun99/zoe/blob/main/docs/EMOJA.md>
- Enforcement status: <https://github.com/karun99/zoe/blob/main/docs/ENFORCEMENT.md>
- Self-check T1–T8: `pytest tests/emoja -q` → 8 passed

**Honest boundary.** Emoja is a reflection surface, not a memory store. If you
want Zoe to remember what a user tells you across sessions, that is Celebrum's
job, with Celebrum's consent and erasure controls. The two projects share a
design commitment — local-first, consent-gated, no covert logging — but neither
writes into the other's store.

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
