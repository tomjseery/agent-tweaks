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
| [Codex hold-to-dictate](tweaks/codex-hold-to-dictate/) | Supported (Kitty protocol + PipeWire) | Planned | Hold Space to dictate into the Codex CLI composer |

## Quick start

```bash
git clone https://github.com/tomjseery/agent-tweaks.git
cd agent-tweaks
./tweaks/codex-hold-to-dictate/linux/install.sh
```

Open a new terminal after installation. Every tweak also includes its own
requirements, controls, troubleshooting instructions, and uninstaller.

Windows support for hold-to-dictate is scaffolded but not yet implemented. The
shared Python behavior is already platform-neutral; the native Windows console
and microphone backend will be added and validated on Windows before being
advertised as supported.

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
tweaks/
└── codex-hold-to-dictate/
    ├── README.md
    ├── dictation_core.py
    ├── linux/
    ├── tests/
    └── windows/
```

New tweaks should follow the same feature-first layout. Reusable code belongs
at the tweak root; operating-system integrations belong in their respective
platform directories.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Bug reports and focused platform ports
are welcome.

## License

[MIT](LICENSE). Third-party speech-recognition models retain their own licenses.

This community project is not affiliated with OpenAI or Anthropic.
