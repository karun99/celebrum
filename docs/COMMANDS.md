# Command reference

Every command you need to install, run, inspect, update, and remove
Celebrum — on Android/Termux and on a desktop.

- [Install](#install)
- [Update](#update)
- [Uninstall](#uninstall)
- [App launcher (`celebrum-app`)](#app-launcher-celebrum-app)
- [Brain CLI (`celebrum`)](#brain-cli-celebrum)
- [Everyday recipes](#everyday-recipes)
- [MCP server](#mcp-server)
- [Files, ports, environment](#files-ports-environment)
- [Troubleshooting](#troubleshooting)

## Install

### Android / Termux (one command)

Install **[Termux](https://f-droid.org/packages/com.termux/)** from F-Droid,
open it, and paste:

```bash
curl -fsSL https://raw.githubusercontent.com/karun99/celebrum/main/install-termux.sh | bash
```

Then start the app:

```bash
celebrum-app
```

The dashboard opens at `http://127.0.0.1:8477`. The installer also creates a
Termux:Widget shortcut in `~/.shortcuts/Celebrum`.

Useful installer flags (append them after `bash -s --` in the one-liner):

```bash
# autostart after reboot (needs the Termux:Boot app)
curl -fsSL https://raw.githubusercontent.com/karun99/celebrum/main/install-termux.sh | bash -s -- --with-boot

# empty brain instead of demo memories
curl -fsSL https://raw.githubusercontent.com/karun99/celebrum/main/install-termux.sh | bash -s -- --no-demo

# different dashboard port
curl -fsSL https://raw.githubusercontent.com/karun99/celebrum/main/install-termux.sh | bash -s -- --port 8686

# install from a local checkout
git clone https://github.com/karun99/celebrum.git
cd celebrum
./install-termux.sh
```

### Desktop / server

```bash
git clone https://github.com/karun99/celebrum.git
cd celebrum
pip install .            # or: pipx install . / uv tool install .
celebrum init --demo
celebrum gui
```

The desktop app launcher can be installed too:

```bash
./install-termux.sh --force
celebrum-app
```

### Docker

```bash
docker build -t celebrum .
docker run --rm -p 8477:8477 celebrum gui --host 0.0.0.0
```

Open `http://localhost:8477`.

## Update

```bash
# Android / Termux
celebrum-app stop
curl -fsSL https://raw.githubusercontent.com/karun99/celebrum/main/install-termux.sh | bash
celebrum-app

# Desktop from a checkout
git pull
pip install .
```

Your brain (`~/.celebrum/celebrum.db`) is never modified by an update.

## Uninstall

```bash
# Android: remove launcher, widget, boot script and venv; keep the brain
curl -fsSL https://raw.githubusercontent.com/karun99/celebrum/main/install-termux.sh | bash -s -- --uninstall

# Remove the brain too
rm -rf ~/.celebrum

# Desktop
pip uninstall celebrum
```

## App launcher (`celebrum-app`)

The one-tap launcher installed on Termux (and optionally on desktop). It runs
the dashboard in the background, waits until it answers, opens the browser,
and posts a notification with **Open** / **Stop** buttons.

| Command | What it does |
|---|---|
| `celebrum-app` | Start the dashboard and open the browser |
| `celebrum-app start` | Same as above (explicit) |
| `celebrum-app stop` | Stop the background dashboard |
| `celebrum-app restart` | Stop, then start |
| `celebrum-app status` | Show running state and URL |
| `celebrum-app open` | Open the dashboard in the browser |
| `celebrum-app url` | Print the dashboard URL |
| `celebrum-app logs` | Show the last 60 log lines |
| `celebrum-app logs -f` | Follow the log live |
| `celebrum-app doctor` | Check binary, python, brain, termux-api, status |
| `celebrum-app version` | Print the Celebrum version |
| `celebrum-app --help` | In-terminal help |

### Flags

| Flag | Meaning |
|---|---|
| `--port N` | Preferred port (default `8477`; next free port is used if busy) |
| `--host H` | Bind address (default `127.0.0.1`; use `0.0.0.0` for LAN) |
| `--no-open` | Do not open the browser |
| `--no-notify` | Do not post the Termux notification |

### Examples

```bash
# Start on another port
celebrum-app start --port 8686

# LAN mode: open http://<phone-ip>:8477 from another device
celebrum-app start --host 0.0.0.0

# Start in the background without opening a browser (boot script)
celebrum-app start --no-open --no-notify

# Is it alive?
celebrum-app status && celebrum-app url

# Why did it fail?
celebrum-app logs -f
```

> The dashboard has no authentication. Use `--host 0.0.0.0` only on a trusted
> network, and stop the app when you are done.

## Brain CLI (`celebrum`)

`celebrum` is the brain itself. All state lives in one SQLite file
(`~/.celebrum/celebrum.db`); override the folder with `--home DIR` (before the
command) or the `CELEBRUM_HOME` environment variable.

```bash
celebrum --help
celebrum <command> [options]
```

### Memory

| Command | Description |
|---|---|
| `celebrum init` | Create the brain store |
| `celebrum init --demo` | Create + seed with the bundled demo memories |
| `celebrum recall "query"` | Identity-grounded recall |
| `celebrum recall "query" -k 10` | Return 10 memories |
| `celebrum recall "query" --no-identity` | Plain recall, without the identity graph |
| `celebrum status` | One-screen summary (neurons, synapses, truth) |
| `celebrum tensor` | Personal Tensor Memory info |

### Ingest (consent required, audit-logged)

| Command | Description |
|---|---|
| `celebrum ingest duet FILE.json` | Duet-style consented memory export |
| `celebrum ingest html FILE.html` | Local HTML knowledge source |
| `celebrum ingest web https://...` | Public page (SSRF-guarded, max 5 MB) |

### Reason

| Command | Description |
|---|---|
| `celebrum persona` | Persona Model + evidence trace |
| `celebrum simulate "scenario"` | Stance and value conflicts |
| `celebrum truth` | Veracity, truth index, contradictions |
| `celebrum validate` | Run the six-check validation harness |
| `celebrum neurobot` | Cognitive-robotics validation (spikes + control loop) |

`neurobot` flags: `--electrodes N` (default 12), `--bins N` (default 32),
`--steps N` (default 40).

### Guardrails

| Command | Description |
|---|---|
| `celebrum propose` | Propose guardrail adaptations (tiered by risk) |
| `celebrum guardrails` | List guardrails and proposals |
| `celebrum decide approve ID` | Approve a proposal |
| `celebrum decide reject ID` | Reject a proposal |
| `celebrum decide revert ID` | Revert a reversible change |
| `celebrum decide approve ID --by NAME` | Record who approved it |

High-tier changes require a human identity (`--by`).

### Data, audit, server

| Command | Description |
|---|---|
| `celebrum graph` | Export the neuron/synapse graph as JSON |
| `celebrum graph --out brain.json` | Write the graph to a file |
| `celebrum audit` | Last 20 audit entries |
| `celebrum audit -n 100` | Last 100 audit entries |
| `celebrum gui` | Start the dashboard (default `127.0.0.1:8477`) |
| `celebrum gui --host 0.0.0.0 --port 8686` | Dashboard on the LAN |
| `celebrum mcp` | MCP stdio server for AI agents |

## Everyday recipes

```bash
# First run
celebrum init --demo
celebrum status
celebrum recall "privacy"
celebrum persona

# Ask the brain what it would think
celebrum simulate "should we log every keystroke?"

# Check the guardrails and truth layer
celebrum propose
celebrum guardrails
celebrum truth

# Ingest your own data (explicit consent)
celebrum ingest duet ~/export.json
celebrum ingest html ~/notes/friend.html
celebrum ingest web https://example.com/article

# Export / back up the graph
celebrum graph --out ~/celebrum-graph.json

# Full health check
celebrum validate
```

On Android, the brain CLI is available after install:

```bash
celebrum status
celebrum recall "privacy"
celebrum-app url
```

## MCP server

Start the stdio server:

```bash
celebrum mcp
```

Add it to any MCP client (Claude Desktop, Cursor, agents):

```json
{
  "mcpServers": {
    "celebrum": {
      "command": "celebrum",
      "args": ["mcp"]
    }
  }
}
```

On Termux, if the client does not inherit your `PATH`, use the full path:

```json
{
  "mcpServers": {
    "celebrum": {
      "command": "/data/data/com.termux/files/usr/bin/celebrum",
      "args": ["mcp"]
    }
  }
}
```

Exposed tools:

| Tool | Purpose |
|---|---|
| `celebrum.recall` | Identity-grounded memory recall |
| `celebrum.simulate` | Stance + value-conflict simulation |
| `celebrum.propose_guardrail` | Propose a guardrail change (audited) |
| `celebrum.approve_guardrail` | Approve (high tier needs a human identity) |
| `celebrum.snapshot` | Snapshot + drift comparison |
| `celebrum.validate` | Run the validation harness |

## Files, ports, environment

### Where things live

| Path | What |
|---|---|
| `~/.celebrum/celebrum.db` | Your brain (one SQLite file) |
| `~/.celebrum/venv/` | Private Python environment (Termux) |
| `~/.celebrum/app.env` | Launcher config (home, venv, port) |
| `~/.celebrum/app.log` | Dashboard log |
| `~/.celebrum/app.pid` | Background dashboard pid |
| `~/.celebrum/app.url` | Current dashboard URL |
| `~/.celebrum/install.log` | Installer output |
| `~/.shortcuts/Celebrum` | Termux:Widget shortcut |
| `~/.termux/boot/celebrum.sh` | Optional Termux:Boot script (with `--with-boot`) |
| `$PREFIX/bin/celebrum` | Brain CLI command |
| `$PREFIX/bin/celebrum-app` | App launcher command |

### Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `CELEBRUM_HOME` | `~/.celebrum` | Brain home folder |
| `CELEBRUM_PORT` | `8477` | Preferred dashboard port |
| `CELEBRUM_HOST` | `127.0.0.1` | Dashboard bind address |
| `CELEBRUM_BIN` | `$CELEBRUM_HOME/venv/bin/celebrum` | CLI used by the launcher |
| `CELEBRUM_PY` | `$CELEBRUM_HOME/venv/bin/python` | Python used by the launcher |
| `CELEBRUM_CMD` | launcher path | Command used by notification buttons |
| `CELEBRUM_DATA_DIR` | bundled data | Override the demo data folder |
| `CELEBRUM_REPO` | `https://github.com/karun99/celebrum.git` | Installer clone remote |
| `CELEBRUM_REF` | `main` | Installer branch/tag |
| `CELEBRUM_SRC` | auto | Install from a local checkout |
| `CELEBRUM_VENV` | `$CELEBRUM_HOME/venv` | Installer venv path |

Examples:

```bash
# Keep the brain somewhere else
CELEBRUM_HOME=~/brains/primary celebrum status

# Or pass it explicitly
celebrum --home ~/brains/primary status
```

### Ports

| Port | Service |
|---|---|
| `8477` | Dashboard (default) |
| any | `celebrum-app --port N` / `celebrum gui --port N` |

The dashboard is local-only (`127.0.0.1`) unless you pass `--host 0.0.0.0`.

## Troubleshooting

```bash
celebrum-app doctor        # launcher, binary, python, brain, termux-api
celebrum-app logs -f       # live dashboard log
celebrum status            # brain summary
celebrum validate          # six-check harness
celebrum --help            # CLI syntax
```

| Problem | Fix |
|---|---|
| `celebrum-app: command not found` | Re-run the installer, then open a new Termux session |
| Browser does not open | Install **Termux:API** (`pkg install termux-api`), or open `celebrum-app url` manually |
| Dashboard dies in the background | `termux-wake-lock`; disable battery optimization for Termux |
| Port busy | `celebrum-app start --port 8686` |
| `termux-notification` hangs | Install the Termux:API app; the launcher times out safely |
| `init --demo` says data missing | Re-run the installer (demo data ships in `share/celebrum/data`) |
| Installer says "not Termux" | Run it inside Termux, not `proot-distro`; or use `--force` |
| `pip` errors during install | `pkg update && pkg upgrade`, then re-run the installer |
| Reset demo data | `celebrum-app stop && rm -rf ~/.celebrum`, then re-install |

Full Android guide: [TERMUX.md](TERMUX.md).
