# Codex hold-to-dictate

A local speech-to-text adapter that gives the Codex CLI the same dictation
gesture as Claude Code:

- tap Space: type a normal space;
- hold Space for 320 ms: start recording locally;
- release Space: stop recording and insert the transcribed text into the
  current Codex prompt.

It affects only Codex processes launched through the `codex` shell alias. It
does not install a global keyboard hook and does not change Claude.

Dictation is external to Codex. Audio stays local and is transcribed with Vosk;
the adapter never invokes Codex `/voice` or starts a voice conversation.

## Compatibility

| Platform | Status |
| --- | --- |
| Linux with a Kitty-keyboard-protocol terminal and PipeWire | Supported |
| Native Windows | [Planned](windows/) |
| WSL | Untested |

The initial Linux implementation was tested on Arch Linux with Kitty. Other
modern terminals implementing the required Kitty key-event flags may work but
have not yet been verified.

The tap-versus-hold state machine and Vosk transcript parsing are shared in
`dictation_core.py`. Linux and Windows keep their console, microphone, process,
and installation code in their own directories.

## Install on Linux

Requirements:

- Codex CLI;
- Python 3.10 or newer;
- the Python `vosk` package;
- PipeWire's `pw-cat` command;
- `curl` and `unzip` when the speech model is not already installed.

On Arch Linux, install the system dependencies:

```sh
pkexec pacman -S --needed git python python-vosk pipewire-audio curl unzip
```

Then, from the Agent Tweaks repository root:

```sh
./tweaks/codex/hold-to-dictate/linux/install.sh
```

The installer:

1. verifies dependencies and locates the real Codex executable;
2. installs the adapter under the user's XDG data directory;
3. downloads the small English Vosk model if needed;
4. adds a marked, removable shell startup hook;
5. creates `codex` and `codex-real` aliases.

Open a new terminal after installation.

The installation survives logouts and restarts. Once installed, normal use is
just opening a supported terminal and running `codex`; do not rerun the
installer after every reboot.

## Controls

- `codex`: launch with hold-to-dictate.
- `codex-real`: bypass the adapter.
- `AGENT_TWEAKS_DISABLE=1 codex-hold-to-dictate`: bypass it for one launch.
- `AGENT_TWEAKS_HOLD_MS=400 codex-hold-to-dictate`: change the hold threshold.
- `AGENT_TWEAKS_VOSK_MODEL=/path/to/model codex-hold-to-dictate`: use another Vosk model.

## Uninstall

```sh
./tweaks/codex/hold-to-dictate/linux/uninstall.sh
```

The shared speech model is preserved so other local dictation tools can keep
using it.

## Privacy

Audio is processed locally by Vosk. The adapter does not upload recordings or
store them on disk.

## Test

```sh
python3 -m unittest discover -s tweaks/codex/hold-to-dictate/tests -v
```
