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

## Linux

Codex hold-to-dictate is supported on Linux with PipeWire and a terminal that
implements the required Kitty keyboard protocol.

### 1. Install prerequisites on Arch Linux

Codex CLI must already be installed. Install the remaining packages with:

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

Use `./install.sh --list` to list supported targets. The installer checks the
dependencies, downloads the small English speech model, and keeps the original
Codex CLI available as `codex-real`.

### After a restart

Nothing needs to be reinstalled. Open a supported terminal and run `codex`.
The installation, local speech model, and shell hook persist, and normal
dictation does not require internet access.

### Uninstall

Remove every installed Linux tweak:

```sh
./uninstall.sh
```

Or remove only Codex hold-to-dictate:

```sh
./uninstall.sh codex/hold-to-dictate
```

See the [Linux tweak README](tweaks/linux/codex/hold-to-dictate/) for controls and
troubleshooting.

## Windows

Native Windows hold-to-dictate is planned but not implemented yet. The shared
Python behavior and root PowerShell dispatchers are ready; the native console
and microphone backend still needs to be implemented and tested on Windows.

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
- Preserve user configuration: installers add small managed hooks instead of
  replacing existing configuration files.

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
│   └── claude/
├── windows/
│   ├── codex/
│   │   └── hold-to-dictate/
│   └── claude/
└── shared/
    ├── codex/
    │   └── hold-to-dictate/
    └── claude/
```

Choose the operating system first, then the agent and tweak. Reusable code lives
under `tweaks/shared/` using the same agent-and-tweak hierarchy.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Bug reports and focused platform ports
are welcome.

## License

[MIT](LICENSE). Third-party speech-recognition models retain their own licenses.

This community project is not affiliated with OpenAI or Anthropic.
