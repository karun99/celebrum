# Celebrum on Android (Termux)

Celebrum is pure Python with no compiled dependencies, so it runs natively on
Android through [Termux](https://termux.dev). The Termux installer makes it
feel like an app: one command on the home screen starts the brain and opens the
dashboard, with a notification that can reopen or stop it.

## What the installer sets up

| Piece | Where |
|---|---|
| Private Python venv | `~/.celebrum/venv` |
| `celebrum` CLI | `$PREFIX/bin/celebrum` |
| `celebrum-app` launcher | `$PREFIX/bin/celebrum-app` |
| Launcher config | `~/.celebrum/app.env` |
| Termux:Widget shortcut | `~/.shortcuts/Celebrum` |
| Optional boot script | `~/.termux/boot/celebrum.sh` |
| Your brain | `~/.celebrum/celebrum.db` |
| Dashboard log | `~/.celebrum/app.log` |

The dashboard binds to `127.0.0.1` only by default. Nothing leaves the phone.

## Requirements

- Termux installed **from F-Droid** (the Play Store build is outdated).
- Android 7+ and ~60 MB of free storage.
- Optional: [Termux:Widget](https://f-droid.org/packages/com.termux.widget/)
  for the home-screen shortcut.
- Optional: [Termux:Boot](https://f-droid.org/packages/com.termux.boot/) for
  autostart after a reboot.
- Optional: [Termux:API](https://f-droid.org/packages/com.termux.api/) plus
  `pkg install termux-api` for notifications and browser opening.

## Install

One-liner (recommended):

```bash
curl -fsSL https://raw.githubusercontent.com/karun99/celebrum/main/install-termux.sh | bash
```

From a checkout:

```bash
git clone https://github.com/karun99/celebrum.git
cd celebrum
./install-termux.sh
```

The installer:

1. installs `python`, `git`, and (optionally) `termux-api` with `pkg`;
2. creates `~/.celebrum/venv` and installs Celebrum into it;
3. adds the `celebrum` and `celebrum-app` commands;
4. seeds a demo brain on first run (skip with `--no-demo`);
5. creates the Termux:Widget shortcut;
6. runs a doctor check.

Useful flags:

```bash
./install-termux.sh --with-boot        # autostart on reboot
./install-termux.sh --no-shortcut      # no home-screen widget
./install-termux.sh --port 8686        # prefer another dashboard port
./install-termux.sh --home ~/brains/x  # store the brain elsewhere
./install-termux.sh --no-demo          # start with an empty brain
./install-termux.sh --update           # pkg update before installing
```

## Use it like an app

```bash
celebrum-app                # start + open the dashboard
celebrum-app open           # reopen it
celebrum-app stop           # stop the background dashboard
celebrum-app restart
celebrum-app status
celebrum-app logs -f
celebrum-app doctor
```

`celebrum-app` starts the dashboard in the background, waits until it actually
answers, then opens the browser. If the preferred port is busy it picks the
next free one. A Termux notification stays in the shade with **Open** and
**Stop** buttons.

### Home-screen widget

1. Install **Termux:Widget** from F-Droid.
2. Long-press the home screen → Widgets → Termux:Widget.
3. Place the widget and tap **Celebrum**.

The shortcut runs `celebrum-app`, so it starts the brain and opens the
dashboard in one tap.

### Autostart on reboot

```bash
./install-termux.sh --with-boot
```

Install **Termux:Boot** and open it once. On boot, the brain starts with
`--no-open --no-notify` so it is ready before you tap the widget.

## Updating

```bash
celebrum-app stop
curl -fsSL https://raw.githubusercontent.com/karun99/celebrum/main/install-termux.sh | bash
celebrum-app
```

If you installed from a checkout, `git pull` and re-run `./install-termux.sh`.
Your brain in `~/.celebrum/celebrum.db` is never touched by an update.

## Backup and restore

Everything is one SQLite file:

```bash
celebrum-app stop
cp ~/.celebrum/celebrum.db ~/storage/shared/celebrum-backup.db
```

Restore by copying the file back while the app is stopped. Run
`termux-setup-storage` once if you want `~/storage/shared` access.

## LAN mode

Reach the dashboard from another device on the same Wi-Fi:

```bash
celebrum-app start --host 0.0.0.0 --port 8477
# then open http://<phone-ip>:8477 from the other device
```

**The dashboard has no authentication.** Only use `--host 0.0.0.0` on a trusted
network, and run `celebrum-app stop` when you are done.

## Uninstall

Remove the launcher, widget, boot script, and venv (brain kept):

```bash
curl -fsSL https://raw.githubusercontent.com/karun99/celebrum/main/install-termux.sh | bash -s -- --uninstall
```

Then delete the brain if you want it gone:

```bash
rm -rf ~/.celebrum
```

## Troubleshooting

**The installer says it is not Termux.** Run it inside Termux, not inside
`proot-distro`, `sudo`, or another shell. A desktop install can be forced with
`--force` (launcher goes to `~/.local/bin`).

**`termux-notification: command not found` / no notification.** Install the
Termux:API app from F-Droid, then `pkg install termux-api`. The launcher still
works without it; it just opens the browser directly.

**The browser does not open.** Install Termux:API, or open the URL printed by
`celebrum-app url` manually.

**The dashboard stops when I leave Termux.** Android may freeze background
apps. Run `termux-wake-lock`, and disable battery optimization for Termux in
Android settings. The optional boot script also requests a wake-lock.

**Port already in use.** The launcher picks the next free port automatically.
Pin one with `celebrum-app start --port 8686`.

**`pip` fails while installing.** Run `pkg update && pkg upgrade`, then
re-run the installer. A copy of the install output is kept at
`~/.celebrum/install.log`.

**`celebrum-app doctor` shows a missing binary.** Re-run the installer; it
reuses the existing venv and reinstalls the package.

**Reset the demo data.** Stop the app and remove the brain:

```bash
celebrum-app stop
rm -rf ~/.celebrum
# then re-run the installer
```
