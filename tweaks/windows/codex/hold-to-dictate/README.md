# Windows support

Status: **planned, not yet implemented**.

The Windows backend will reuse the platform-neutral
[`dictation_core.py`](../../../shared/codex/hold-to-dictate/dictation_core.py).
Only the console, microphone, process, and installer layers need a native
implementation.

The Linux adapter cannot simply be copied to native Windows because it relies
on POSIX PTYs, Unix signals, PipeWire, and terminal key-release reporting.

## Behavioural contract

A Windows implementation must provide the same user-facing behaviour:

- a tap of Space inserts one ordinary space;
- holding Space beyond the configured threshold starts local recording;
- releasing Space stops recording and inserts the transcript at the current
  Codex composer cursor;
- pasted spaces and modified Space keys are never treated as dictation;
- the interception applies only to the wrapped Codex CLI process;
- Codex `/voice` is never invoked;
- a bypass command launches the unwrapped Codex CLI;
- installation and uninstallation preserve existing user configuration.

## Likely native design

The native implementation will need:

1. A ConPTY-based Codex wrapper or another process-scoped console input layer.
2. Windows key-down/key-up handling that does not install an unrestricted
   system-wide Space hook.
3. Windows microphone capture through an appropriate local API.
4. Local speech recognition, with Vosk as the initial compatibility target.
5. PowerShell install and uninstall scripts.
6. Tests matching the Linux tap/hold/release fixtures.

Implement and validate this on an actual Windows machine before changing the
root compatibility table to Supported.

## WSL

WSL is also untested. Although the wrapper code is Linux-oriented, microphone
capture and terminal key-release support depend on the Windows host and
terminal. Treat WSL as a separate target rather than assuming Linux support
applies automatically.
