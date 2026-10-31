#!/usr/bin/env bash
# Celebrum - Termux / Android installer.
#
# Turns Celebrum into a one-tap phone app: installs Python + the brain in a
# private venv, adds `celebrum` and `celebrum-app` commands, creates a
# Termux:Widget home-screen shortcut, an optional Termux:Boot autostart, and
# seeds a demo brain on first run.
#
# One-liner:
#   curl -fsSL https://raw.githubusercontent.com/karun99/celebrum/main/install-termux.sh | bash
#
# From a checkout:
#   ./install-termux.sh
#
# Options:
#   --repo URL         git remote to clone when not run from a checkout
#   --ref BRANCH       branch/tag to install (default: main)
#   --src DIR          install from an existing local checkout instead
#   --venv DIR         virtualenv location (default: ~/.celebrum/venv)
#   --bin-dir DIR      where to put the celebrum / celebrum-app commands
#   --home DIR         brain home (default: ~/.celebrum)
#   --port N           preferred dashboard port (default: 8477)
#   --no-demo          create an empty brain instead of seeding demo memories
#   --no-shortcut      skip the Termux:Widget shortcut
#   --with-boot        add a Termux:Boot autostart script
#   --no-termux-api    do not install termux-api (no notifications)
#   --update           install pkg updates first
#   --uninstall        remove the launcher, shortcut, boot script and venv
#   --force            allow running outside Termux (desktop install)
#   --yes              assume yes for package installs
#   -h, --help         show this help

set -Eeuo pipefail

REPO="${CELEBRUM_REPO:-https://github.com/karun99/celebrum.git}"
REF="${CELEBRUM_REF:-main}"
APP_HOME="${CELEBRUM_HOME:-$HOME/.celebrum}"
VENV="${CELEBRUM_VENV:-$APP_HOME/venv}"
PORT="${CELEBRUM_PORT:-8477}"
DEMO=1
SHORTCUT=1
BOOT=0
WITH_API=1
DO_UPDATE=0
FORCE=0
UNINSTALL=0
SRC_OPT=""
BIN_DIR_OPT=""

bold() { printf '\033[1m%s\033[0m\n' "$*"; }
step() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m  ok\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m  warn\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Celebrum - Termux / Android installer.

Turns Celebrum into a one-tap phone app: installs Python + the brain in a
private venv, adds `celebrum` and `celebrum-app` commands, creates a
Termux:Widget home-screen shortcut, an optional Termux:Boot autostart, and
seeds a demo brain on first run.

One-liner:
  curl -fsSL https://raw.githubusercontent.com/karun99/celebrum/main/install-termux.sh | bash

From a checkout:
  ./install-termux.sh

Options:
  --repo URL         git remote to clone when not run from a checkout
  --ref BRANCH       branch/tag to install (default: main)
  --src DIR          install from an existing local checkout instead
  --venv DIR         virtualenv location (default: ~/.celebrum/venv)
  --bin-dir DIR      where to put the celebrum / celebrum-app commands
  --home DIR         brain home (default: ~/.celebrum)
  --port N           preferred dashboard port (default: 8477)
  --no-demo          create an empty brain instead of seeding demo memories
  --no-shortcut      skip the Termux:Widget shortcut
  --with-boot        add a Termux:Boot autostart script
  --no-termux-api    do not install termux-api (no notifications)
  --update           install pkg updates first
  --uninstall        remove the launcher, shortcut, boot script and venv
  --force            allow running outside Termux (desktop install)
  --yes              assume yes for package installs
  -h, --help         show this help
EOF
}

# ---- parse args ------------------------------------------------------------
need_val() {
  [ "$2" -ge 2 ] || die "$1 needs a value"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --repo) need_val "$1" $#;          REPO="$2"; shift ;;
    --repo=*)        REPO="${1#*=}" ;;
    --ref) need_val "$1" $#;           REF="$2"; shift ;;
    --ref=*)         REF="${1#*=}" ;;
    --src) need_val "$1" $#;           SRC_OPT="$2"; shift ;;
    --src=*)         SRC_OPT="${1#*=}" ;;
    --venv) need_val "$1" $#;          VENV="$2"; shift ;;
    --venv=*)        VENV="${1#*=}" ;;
    --bin-dir) need_val "$1" $#;       BIN_DIR_OPT="$2"; shift ;;
    --bin-dir=*)     BIN_DIR_OPT="${1#*=}" ;;
    --home) need_val "$1" $#;          APP_HOME="$2"; shift ;;
    --home=*)        APP_HOME="${1#*=}" ;;
    --port) need_val "$1" $#;          PORT="$2"; shift ;;
    --port=*)        PORT="${1#*=}" ;;
    --no-demo)       DEMO=0 ;;
    --no-shortcut)   SHORTCUT=0 ;;
    --with-boot)     BOOT=1 ;;
    --no-termux-api) WITH_API=0 ;;
    --update)        DO_UPDATE=1 ;;
    --uninstall)     UNINSTALL=1 ;;
    --force)         FORCE=1 ;;
    -y|--yes)        : ;;
    -h|--help)       usage; exit 0 ;;
    *) die "unknown option: $1 (try --help)" ;;
  esac
  shift
done

is_termux() {
  [ -n "${TERMUX_VERSION:-}" ] \
    || [ "${PREFIX:-}" = "/data/data/com.termux/files/usr" ] \
    || case "${PREFIX:-}" in *com.termux*) true ;; *) false ;; esac
}

TERMUX=0
is_termux && TERMUX=1

if [ "$TERMUX" = 0 ] && [ "$FORCE" = 0 ]; then
  warn "this installer is for Termux on Android."
  warn "on a desktop use: pip install . && celebrum gui"
  warn "re-run with --force to install the desktop app launcher anyway."
  exit 1
fi

# $PREFIX/bin on Termux, ~/.local/bin elsewhere.
if [ -n "$BIN_DIR_OPT" ]; then
  BIN_DIR="$BIN_DIR_OPT"
elif [ -n "${PREFIX:-}" ]; then
  BIN_DIR="$PREFIX/bin"
else
  BIN_DIR="$HOME/.local/bin"
fi

BASH_BIN="$(command -v bash || printf '/bin/bash')"
log_file="$APP_HOME/install.log"
mkdir -p "$APP_HOME"
# Mirror the install output into a log when the shell supports process
# substitution (Termux does); otherwise keep everything on the terminal.
if ( : > >(cat >/dev/null) ) 2>/dev/null; then
  exec > >(tee -a "$log_file") 2>&1
fi

if [ "$UNINSTALL" = 1 ]; then
  step "uninstalling Celebrum app pieces"
  [ -f "$APP_HOME/app.pid" ] && kill "$(cat "$APP_HOME/app.pid")" 2>/dev/null || true
  rm -f "$BIN_DIR/celebrum-app" "$BIN_DIR/celebrum"
  rm -f "$APP_HOME/celebrum-app"
  rm -f "$HOME/.shortcuts/Celebrum" "$HOME/.termux/boot/celebrum.sh"
  if [ "$TERMUX" = 1 ] && command -v termux-notification >/dev/null 2>&1; then
    if command -v timeout >/dev/null 2>&1; then
      timeout 5 termux-notification --id celebrum --remove >/dev/null 2>&1 || true
    else
      termux-notification --id celebrum --remove >/dev/null 2>&1 || true
    fi
  fi
  rm -rf "$VENV"
  rm -f "$APP_HOME/app.env" "$APP_HOME/app.url" "$APP_HOME/app.pid" "$APP_HOME/app.log"
  ok "removed launcher + venv"
  echo "Your brain data was kept at $APP_HOME/celebrum.db"
  echo "Delete it yourself with: rm -rf \"$APP_HOME\""
  exit 0
fi

# ---- checks ----------------------------------------------------------------
step "checking the device"
if [ "$TERMUX" = 1 ]; then
  ok "Termux detected (${TERMUX_VERSION:-unknown version})"
  [ -n "${ANDROID_ROOT:-}" ] && [ -d "$HOME" ] && ok "home: $HOME" || true
else
  ok "desktop mode (--force)"
fi

case "$(uname -m)" in
  aarch64|arm64) ok "arch: arm64" ;;
  armv7l|armv8l) ok "arch: arm32" ;;
  x86_64|i686)   ok "arch: x86_64 (Termux emulator)" ;;
  *) warn "unknown arch: $(uname -m) - pure-python, should still work" ;;
esac

# ---- system packages -------------------------------------------------------
if [ "$TERMUX" = 1 ]; then
  step "installing Termux packages"
  if [ "$DO_UPDATE" = 1 ]; then
    pkg update -y || warn "pkg update failed, continuing"
  fi
  pkg install -y python git || die "pkg install python git failed"
  ok "python $(python3 -V 2>&1 | awk '{print $2}') + git"
  if [ "$WITH_API" = 1 ] && ! command -v termux-notification >/dev/null 2>&1; then
    pkg install -y termux-api >/dev/null 2>&1 \
      && ok "termux-api installed (notifications)" \
      || warn "termux-api not installed - the app still works, no notifications"
  fi
else
  command -v python3 >/dev/null 2>&1 || die "python3 is required"
  command -v git >/dev/null 2>&1 || warn "git missing - using local source only"
fi

command -v python3 >/dev/null 2>&1 || die "python3 not found after install"
python3 - <<'PY' || die "Python 3.9+ is required"
import sys
raise SystemExit(0 if sys.version_info >= (3, 9) else 1)
PY
ok "python version ok"

# ---- source ----------------------------------------------------------------
step "fetching Celebrum"
SRC=""
if [ -n "$SRC_OPT" ]; then
  SRC="$SRC_OPT"
elif [ -n "${CELEBRUM_SRC:-}" ]; then
  SRC="$CELEBRUM_SRC"
elif [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  [ -f "$here/pyproject.toml" ] && SRC="$here" || true
fi

if [ -z "$SRC" ] || [ ! -f "$SRC/pyproject.toml" ]; then
  SRC="$APP_HOME/src/celebrum"
  if [ -d "$SRC/.git" ]; then
    step "updating source at $SRC"
    git -C "$SRC" fetch --depth 1 origin "$REF" \
      && git -C "$SRC" checkout -q FETCH_HEAD \
      || warn "git update failed, reusing existing checkout"
  else
    step "cloning $REPO ($REF)"
    mkdir -p "$(dirname "$SRC")"
    git clone --depth 1 --branch "$REF" "$REPO" "$SRC" \
      || git clone --depth 1 "$REPO" "$SRC" \
      || die "could not clone $REPO"
  fi
fi
[ -f "$SRC/pyproject.toml" ] || die "Celebrum source not found at $SRC"
ok "source: $SRC"

# ---- virtualenv ------------------------------------------------------------
step "creating the app environment"
mkdir -p "$APP_HOME"
if [ -x "$VENV/bin/python" ]; then
  ok "reusing venv at $VENV"
else
  python3 -m venv "$VENV" || die "could not create venv at $VENV (try: pkg install python)"
  ok "venv at $VENV"
fi

step "installing Celebrum (pure python, no compiled deps)"
"$VENV/bin/python" -m pip install --quiet --upgrade pip setuptools wheel \
  || warn "pip self-upgrade failed, continuing"
"$VENV/bin/python" -m pip install --quiet --upgrade "$SRC" \
  || die "pip install failed - see $log_file"
ok "installed $("$VENV/bin/python" -c 'import celebrum; print("celebrum", celebrum.__version__)' 2>/dev/null || echo celebrum)"

# ---- commands --------------------------------------------------------------
step "installing the app commands"
mkdir -p "$BIN_DIR" || die "cannot create $BIN_DIR"
[ -w "$BIN_DIR" ] || die "$BIN_DIR is not writable - pass --bin-dir DIR"

write_wrapper() {
  local name="$1" target="$2"
  {
    printf '#!%s\n' "$BASH_BIN"
    printf 'export CELEBRUM_HOME=%q\n' "$APP_HOME"
    printf 'exec %q "$@"\n' "$target"
  } >"$BIN_DIR/$name"
  chmod 755 "$BIN_DIR/$name"
}

write_wrapper celebrum "$VENV/bin/celebrum"
ok "$BIN_DIR/celebrum"

LAUNCHER_SRC="$SRC/scripts/termux/celebrum-app"
[ -f "$LAUNCHER_SRC" ] || die "launcher missing from source: $LAUNCHER_SRC"
LAUNCHER_REAL="$APP_HOME/celebrum-app"
cp "$LAUNCHER_SRC" "$LAUNCHER_REAL"
chmod 755 "$LAUNCHER_REAL"
write_wrapper celebrum-app "$LAUNCHER_REAL"
ok "$BIN_DIR/celebrum-app"

# Generated launcher config (sourceable shell).
{
  printf '# Generated by install-termux.sh - safe to delete\n'
  printf 'CELEBRUM_HOME=%q\n' "$APP_HOME"
  printf 'CELEBRUM_BIN=%q\n' "$VENV/bin/celebrum"
  printf 'CELEBRUM_PY=%q\n' "$VENV/bin/python"
  printf 'CELEBRUM_PORT=%q\n' "$PORT"
  printf 'CELEBRUM_HOST=%q\n' "127.0.0.1"
  printf 'CELEBRUM_CMD=%q\n' "$BIN_DIR/celebrum-app"
} >"$APP_HOME/app.env"
chmod 600 "$APP_HOME/app.env"

# Make sure the command is reachable on desktops (Termux already has $PREFIX/bin).
case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    if [ -n "${HOME:-}" ] && [ -f "$HOME/.bashrc" ] \
       && ! grep -q "celebrum-termux-installer" "$HOME/.bashrc" 2>/dev/null; then
      {
        printf '\n# celebrum-termux-installer\n'
        printf 'export PATH="%s:$PATH"\n' "$BIN_DIR"
      } >>"$HOME/.bashrc"
      ok "added $BIN_DIR to ~/.bashrc PATH"
    fi
    ;;
esac

# ---- first brain -----------------------------------------------------------
step "preparing your brain"
export CELEBRUM_HOME="$APP_HOME"
if [ -f "$APP_HOME/celebrum.db" ]; then
  ok "existing brain kept at $APP_HOME/celebrum.db"
elif [ "$DEMO" = 1 ]; then
  if "$VENV/bin/celebrum" init --demo >/dev/null 2>&1; then
    ok "seeded a demo brain at $APP_HOME"
  else
    "$VENV/bin/celebrum" init >/dev/null 2>&1 || warn "brain init failed - run: celebrum init"
    warn "demo seed failed, created an empty brain"
  fi
else
  "$VENV/bin/celebrum" init >/dev/null 2>&1 || warn "brain init failed - run: celebrum init"
  ok "empty brain at $APP_HOME"
fi

# ---- home screen shortcut --------------------------------------------------
if [ "$SHORTCUT" = 1 ]; then
  step "creating the home-screen shortcut"
  mkdir -p "$HOME/.shortcuts"
  {
    printf '#!%s\n' "$BASH_BIN"
    printf 'exec %q start\n' "$BIN_DIR/celebrum-app"
  } >"$HOME/.shortcuts/Celebrum"
  chmod 755 "$HOME/.shortcuts/Celebrum"
  ok "$HOME/.shortcuts/Celebrum (needs the Termux:Widget app)"
fi

# ---- optional boot autostart ----------------------------------------------
if [ "$BOOT" = 1 ]; then
  step "adding Termux:Boot autostart"
  mkdir -p "$HOME/.termux/boot"
  {
    printf '#!%s\n' "$BASH_BIN"
    printf 'if command -v timeout >/dev/null 2>&1; then\n'
    printf '  timeout 5 termux-wake-lock >/dev/null 2>&1 || true\n'
    printf 'else\n'
    printf '  termux-wake-lock >/dev/null 2>&1 || true\n'
    printf 'fi\n'
    printf '%q start --no-open --no-notify\n' "$BIN_DIR/celebrum-app"
  } >"$HOME/.termux/boot/celebrum.sh"
  chmod 755 "$HOME/.termux/boot/celebrum.sh"
  ok "$HOME/.termux/boot/celebrum.sh (needs the Termux:Boot app)"
fi

# ---- verify ----------------------------------------------------------------
step "verifying the install"
if "$VENV/bin/celebrum" status >/dev/null 2>&1; then
  ok "CLI works"
else
  warn "CLI check failed - see $log_file"
fi
"$BIN_DIR/celebrum-app" doctor || warn "doctor reported issues"

# ---- done ------------------------------------------------------------------
cat <<EOF

$(bold "Celebrum is now an app on this device.")

  Start it          $ celebrum-app
  Open dashboard    $ celebrum-app open
  Stop it           $ celebrum-app stop
  Logs              $ celebrum-app logs -f
  One-tap widget    add the Termux:Widget to your home screen,
                    then tap "Celebrum"
  Brain data        $APP_HOME/celebrum.db

The dashboard opens at http://127.0.0.1:$PORT (the launcher picks a free
port if that one is busy). Everything stays on this phone.

For LAN access (another device on the same Wi-Fi):
  celebrum-app start --host 0.0.0.0

Uninstall the app pieces (keeps your brain):
  curl -fsSL https://raw.githubusercontent.com/karun99/celebrum/main/install-termux.sh | bash -s -- --uninstall

EOF
