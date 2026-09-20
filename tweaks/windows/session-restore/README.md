# Session Restore for Windows

Status: **planned, not yet implemented**.

The Windows backend will reuse the manifest logic under
`tweaks/shared/session-restore/` and provide:

- live Codex and Claude session discovery without agent hooks;
- periodic private snapshots;
- Windows Terminal restoration;
- a Start menu and desktop shortcut;
- a per-user background task or service;
- PowerShell installation and uninstallation.

Implement and test this on an actual Windows machine before registering it as a
supported target in the root PowerShell dispatchers.
