# Session Restore for Linux

Reopen the Codex and Claude CLI sessions that were running before logout,
restart, shutdown, or power loss.

Session Restore runs as a quiet systemd user service. It reads the local live
session metadata already maintained by Codex and Claude, then stores a small
private manifest under the user's XDG state directory. It does not install
agent hooks, inject prompts, consume tokens, or modify agent configuration.

## What is restored

- the exact Codex or Claude conversation;
- its working directory;
- its saved display name when available;
- one terminal tab or window per session.

Konsole is preferred and opens additional sessions as tabs. Kitty and the
system's `x-terminal-emulator` fallback are also supported.

Unsent composer text, arbitrary child processes, and terminal scrollback cannot
be recovered after the operating system has stopped them.

## Install

From the repository root:

```sh
./install.sh session-restore
```

This installs the tracker, starts it for the current user, and adds **Restore
Sessions** to both the KDE application menu and desktop.

## Commands

`sr` is the short global command; `session-restore` remains available as its
descriptive equivalent.

```sh
sr list
sr snapshot
sr restore
sr restore --dry-run
sr doctor
sr clear
```

The service normally handles snapshots automatically. `snapshot` exists for
manual verification; `clear` forgets the saved workspace without deleting any
Codex or Claude conversations.

## Privacy

The manifest contains agent names, local session identifiers, working-directory
paths, and optional session display names. It is stored locally with permissions
restricted to the current user. Conversation content is never copied.

## Uninstall

```sh
./uninstall.sh session-restore
```
