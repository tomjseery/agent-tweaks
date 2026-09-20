# Agent Tweaks

[![tests](https://github.com/tomjseery/agent-tweaks/actions/workflows/tests.yml/badge.svg)](https://github.com/tomjseery/agent-tweaks/actions/workflows/tests.yml)

Small, optional quality-of-life improvements for AI coding agents.

Agent Tweaks is a home for focused fixes that belong outside an agent's normal
configuration: terminal adapters, input helpers, desktop integrations, and
workflow improvements. Each tweak is independently installable and documents
exactly what it changes.

## Available tweaks

| Tweak | Linux | Windows | Purpose |
| --- | --- | --- | --- |
| Codex hold-to-dictate | [Supported](tweaks/linux/codex/hold-to-dictate/) | [Planned](tweaks/windows/codex/hold-to-dictate/) | Hold Space to dictate into the Codex CLI composer |
| Session Restore | [Supported](tweaks/linux/session-restore/) | [Planned](tweaks/windows/session-restore/) | Reopen Codex and Claude sessions after a restart |

## Linux

Linux currently supports Codex hold-to-dictate and Session Restore. Session
Restore works with both Codex and Claude without agent hooks.

### 1. Install prerequisites on Arch Linux

Codex CLI, Claude Code, or both must already be installed. Install the remaining
packages for all current tweaks with:

```sh
pkexec pacman -S --needed git python python-vosk pipewire-audio curl unzip
```

### 2. Clone the repository

```sh
git clone https://github.com/tomjseery/agent-tweaks.git
cd agent-tweaks
```

### 3. Install

Install every stable Linux tweak:

```sh
./install.sh
```

Or install only Codex hold-to-dictate:

```sh
./install.sh codex/hold-to-dictate
```

Or install only Session Restore:

```sh
./install.sh session-restore
```

Use `./install.sh --list` to list supported targets. The installer checks the
dependencies. Hold-to-dictate downloads its local English speech model and
keeps the original Codex CLI available as `codex-real`. Session Restore adds a
silent user service, a **Restore Sessions** desktop shortcut, and the global
short command `sr` when that name is available.

### After a restart

Nothing needs to be reinstalled. Open a supported terminal and run `codex`, or
use the **Restore Sessions** desktop icon to reopen the agents that were active
before shutdown. The installations and local state persist.

### Uninstall

Remove every installed Linux tweak:

```sh
./uninstall.sh
```

Or remove only Codex hold-to-dictate:

```sh
./uninstall.sh codex/hold-to-dictate
```

Or remove only Session Restore:

```sh
./uninstall.sh session-restore
```

See the individual Linux tweak READMEs for controls and troubleshooting.

## Windows

Native Windows implementations of both tweaks are planned but not implemented
yet. Their shared Python behavior and root PowerShell dispatchers are ready;
the native backends still need to be implemented and tested on Windows.

### 1. Clone the repository

```powershell
git clone https://github.com/tomjseery/agent-tweaks.git
Set-Location agent-tweaks
```

### 2. Install

Install every stable Windows tweak:

```powershell
.\install.ps1
```

Or install only Codex hold-to-dictate:

```powershell
.\install.ps1 codex/hold-to-dictate
```

The future Session Restore target will be:

```powershell
.\install.ps1 session-restore
```

Until the Windows backend is finished, these commands safely report that no
stable Windows tweaks are available instead of changing the system.

### Uninstall

```powershell
.\uninstall.ps1
```

Or target one tweak:

```powershell
.\uninstall.ps1 codex/hold-to-dictate
```

## Keeping only your operating system

You may delete `tweaks/linux/` from a Windows-only clone. Likewise, on Linux you
may delete `tweaks/windows/`. Always retain `tweaks/shared/`. This cleanup is
optional because the root installer ignores the other platform automatically.
Deleting tracked folders will appear as local changes in Git, so keep both if
you plan to pull updates or contribute.

## Project principles

- Opt in: tweaks do nothing until explicitly installed.
- Narrowly scoped: integrations affect only the intended agent or application.
- Reversible: every installer has a matching uninstaller.
- Local first: avoid cloud services when an effective local implementation is
  available.
- Honest compatibility: an operating system is marked supported only after an
  implementation has been tested there.
- Preserve user configuration: installers add only the small managed files
  they need instead of replacing existing configuration files.

## Repository layout

```text
install.sh
install.ps1
uninstall.sh
uninstall.ps1
tweaks/
├── linux/
│   ├── codex/
│   │   └── hold-to-dictate/
│   ├── claude/
│   └── session-restore/
├── windows/
│   ├── codex/
│   │   └── hold-to-dictate/
│   ├── claude/
│   └── session-restore/
└── shared/
    ├── codex/
    │   └── hold-to-dictate/
    ├── claude/
    └── session-restore/
```

Choose the operating system first, then the agent and tweak. Cross-agent tweaks
such as Session Restore live directly under the operating-system folder.
Reusable platform-neutral code lives under `tweaks/shared/`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Bug reports and focused platform ports
are welcome.

## License

[MIT](LICENSE). Third-party speech-recognition models retain their own licenses.

This community project is not affiliated with OpenAI or Anthropic.
