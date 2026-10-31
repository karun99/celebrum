# Installation

## Desktop / server

Pure Python 3.9+, no compiled dependencies:

```bash
git clone https://github.com/karun99/celebrum.git
cd celebrum
pip install .        # or: pipx install . / uv tool install .
celebrum init --demo
celebrum gui         # http://localhost:8477
```

## Android (Termux)

One command installs the brain and a one-tap `celebrum-app` launcher:

```bash
curl -fsSL https://raw.githubusercontent.com/karun99/celebrum/main/install-termux.sh | bash
celebrum-app
```

The launcher starts the dashboard, opens the browser, and adds a Termux:Widget
home-screen shortcut (plus optional Termux:Boot autostart). See
[TERMUX.md](TERMUX.md) for the full guide, LAN mode, and troubleshooting.

## Verify

```bash
celebrum status
celebrum validate
```

For the test suite:

```bash
pip install pytest
pytest -q
```
