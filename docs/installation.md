# Installation

## Quick start

### Android / Termux (one command)

```bash
curl -fsSL https://raw.githubusercontent.com/karun99/celebrum/main/install-termux.sh | bash
celebrum-app
```

That installs Python + Celebrum in a private venv, seeds a demo brain, adds the
`celebrum` and `celebrum-app` commands, and creates a Termux:Widget shortcut.
The dashboard opens at `http://127.0.0.1:8477`.

Full Android guide, including the widget, boot autostart, LAN mode and
uninstall: [TERMUX.md](TERMUX.md).

### Desktop / server

Pure Python 3.9+, no compiled dependencies:

```bash
git clone https://github.com/karun99/celebrum.git
cd celebrum
pip install .        # or: pipx install . / uv tool install .
celebrum init --demo
celebrum gui         # http://localhost:8477
```

### Docker

```bash
docker build -t celebrum .
docker run --rm -p 8477:8477 celebrum gui --host 0.0.0.0
```

## Verify

```bash
celebrum status
celebrum validate
```

Run the test suite:

```bash
pip install pytest
pytest -q
```

## Next

- [Command reference](COMMANDS.md) — every CLI and app command
- [Usage](usage.md) — a tour of the brain
- [FAQ](faq.md) — common questions
