#!/usr/bin/env python3
"""Run Codex with Claude-like hold-Space dictation.

This is a narrowly scoped terminal adapter.  It proxies Codex through a PTY,
asks a compatible terminal for key-release events, and reserves only a held
Space key. A held Space records local audio and inserts speech-to-text into the
composer; a tapped Space is forwarded to Codex as ordinary text.
"""

from __future__ import annotations

import errno
import fcntl
import os
import pty
import re
import select
import signal
import subprocess
import sys
import termios
import threading
import time
from collections.abc import Callable
from pathlib import Path


TWEAK_ROOT = Path(__file__).resolve().parent.parent
if (TWEAK_ROOT / "dictation_core.py").is_file():
    sys.path.insert(0, str(TWEAK_ROOT))
else:
    # The installer places the platform entry point and shared core together.
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from dictation_core import HoldSpace, VOSK_MODEL_NAME, vosk_text


CODEX_KEYBOARD_MODE = b"\x1b[>7u"
# Add "report all keys" and "report associated text" to Codex's requested
# Kitty keyboard mode.  This gives us Space release events.  InputNormalizer
# converts everything except Space back to the mode Codex requested.
PTT_KEYBOARD_MODE = b"\x1b[>31u"
BRACKETED_PASTE_START = b"\x1b[200~"
BRACKETED_PASTE_END = b"\x1b[201~"


def _find_real_codex() -> str | None:
    """Find Codex on PATH while avoiding this wrapper if it shadows `codex`."""

    override = os.environ.get("AGENT_TWEAKS_CODEX_BIN")
    if override:
        return str(Path(override).expanduser())

    wrapper = Path(__file__).resolve()
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory or ".") / "codex"
        try:
            if (
                candidate.is_file()
                and os.access(candidate, os.X_OK)
                and candidate.resolve() != wrapper
            ):
                return str(candidate)
        except OSError:
            continue
    return None


def _default_model_path() -> Path:
    override = os.environ.get("AGENT_TWEAKS_VOSK_MODEL") or os.environ.get("CODEX_DICTATION_MODEL")
    if override:
        return Path(override).expanduser()

    data_home = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
    candidates = (
        data_home / "agent-tweaks/models" / VOSK_MODEL_NAME,
        Path.home() / ".config/vosk-models" / VOSK_MODEL_NAME,
    )
    return next((candidate for candidate in candidates if candidate.is_dir()), candidates[0])


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        try:
            written = os.write(fd, view)
        except InterruptedError:
            continue
        view = view[written:]


class OutputModeRewriter:
    """Rewrite Codex's keyboard-mode request without corrupting split chunks."""

    def __init__(self, on_mode_enabled: Callable[[], None]) -> None:
        self._buffer = bytearray()
        self._on_mode_enabled = on_mode_enabled

    def feed(self, data: bytes) -> bytes:
        self._buffer.extend(data)
        output = bytearray()

        while True:
            index = self._buffer.find(CODEX_KEYBOARD_MODE)
            if index >= 0:
                output.extend(self._buffer[:index])
                output.extend(PTT_KEYBOARD_MODE)
                del self._buffer[: index + len(CODEX_KEYBOARD_MODE)]
                self._on_mode_enabled()
                continue

            keep = 0
            max_keep = min(len(self._buffer), len(CODEX_KEYBOARD_MODE) - 1)
            for size in range(max_keep, 0, -1):
                if self._buffer[-size:] == CODEX_KEYBOARD_MODE[:size]:
                    keep = size
                    break
            if keep:
                output.extend(self._buffer[:-keep])
                del self._buffer[:-keep]
            else:
                output.extend(self._buffer)
                self._buffer.clear()
            return bytes(output)

    def flush(self) -> bytes:
        result = bytes(self._buffer)
        self._buffer.clear()
        return result


class DictationController:
    """Record locally while Space is held and insert the transcript in Codex."""

    def __init__(self, send: Callable[[bytes], None], model_path: Path) -> None:
        self._send = send
        self._model_path = model_path
        self._model: object | None = None
        self._model_error: str | None = None
        self._model_ready = threading.Event()
        self._recorder: subprocess.Popen[bytes] | None = None
        self._reader: threading.Thread | None = None
        self._recognizer: object | None = None
        self._segments: list[str] = []
        threading.Thread(target=self._load_model, daemon=True).start()

    def _load_model(self) -> None:
        try:
            import vosk

            vosk.SetLogLevel(-1)
            if not self._model_path.is_dir():
                raise FileNotFoundError(f"Vosk model not found: {self._model_path}")
            self._model = vosk.Model(str(self._model_path))
        except Exception as error:  # Reported as a desktop notification on use.
            self._model_error = str(error)
        finally:
            self._model_ready.set()

    def _notify(self, message: str) -> None:
        try:
            subprocess.Popen(
                ["notify-send", "Codex dictation", message],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            pass

    def hold_started(self) -> None:
        if self._recorder is not None:
            return
        if not self._model_ready.wait(timeout=3.0) or self._model is None:
            self._notify(self._model_error or "Speech model is still loading")
            return

        try:
            import vosk

            recognizer = vosk.KaldiRecognizer(self._model, 16000)
            recorder = subprocess.Popen(
                [
                    "pw-cat",
                    "--record",
                    "--format=s16",
                    "--rate",
                    "16000",
                    "--channels=1",
                    "-",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, RuntimeError) as error:
            self._notify(f"Could not start the microphone: {error}")
            return

        self._recognizer = recognizer
        self._recorder = recorder
        self._segments = []
        self._reader = threading.Thread(
            target=self._read_audio,
            args=(recorder, recognizer),
            daemon=True,
        )
        self._reader.start()

    def _read_audio(self, recorder: subprocess.Popen[bytes], recognizer: object) -> None:
        if recorder.stdout is None:
            return
        while True:
            data = recorder.stdout.read(4000)
            if not data:
                return
            if recognizer.AcceptWaveform(data):
                text = vosk_text(recognizer.Result())
                if text:
                    self._segments.append(text)

    def hold_released(self) -> None:
        recorder = self._recorder
        recognizer = self._recognizer
        reader = self._reader
        if recorder is None or recognizer is None:
            return

        try:
            recorder.send_signal(signal.SIGINT)
            recorder.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            recorder.terminate()
            try:
                recorder.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                recorder.kill()
        if reader is not None:
            reader.join(timeout=2.0)

        final_text = vosk_text(recognizer.FinalResult())
        transcript = " ".join([*self._segments, final_text]).strip()
        self._recorder = None
        self._reader = None
        self._recognizer = None
        self._segments = []
        if transcript:
            self._send(transcript.encode("utf-8"))

    def close(self) -> None:
        recorder = self._recorder
        self._recorder = None
        if recorder is not None and recorder.poll() is None:
            recorder.terminate()


class InputNormalizer:
    """Normalize Kitty's all-key mode and intercept unmodified Space."""

    _CSI_U = re.compile(rb"^\x1b\[([^u]*)u$")

    def __init__(self, emit: Callable[[bytes], None], hold_space: HoldSpace) -> None:
        self._emit = emit
        self._hold_space = hold_space
        self._buffer = bytearray()
        self._in_paste = False
        self._text_keys_down: set[int] = set()

    def feed(self, data: bytes, now: float) -> None:
        self._buffer.extend(data)
        while self._buffer:
            if self._in_paste:
                index = self._buffer.find(BRACKETED_PASTE_END)
                if index >= 0:
                    end = index + len(BRACKETED_PASTE_END)
                    self._emit(bytes(self._buffer[:end]))
                    del self._buffer[:end]
                    self._in_paste = False
                    continue

                keep = 0
                max_keep = min(len(self._buffer), len(BRACKETED_PASTE_END) - 1)
                for size in range(max_keep, 0, -1):
                    if self._buffer[-size:] == BRACKETED_PASTE_END[:size]:
                        keep = size
                        break
                if keep:
                    self._emit(bytes(self._buffer[:-keep]))
                    del self._buffer[:-keep]
                else:
                    self._emit(bytes(self._buffer))
                    self._buffer.clear()
                return

            if self._buffer[0] != 0x1B:
                index = self._buffer.find(b"\x1b")
                if index < 0:
                    index = len(self._buffer)
                plain = bytes(self._buffer[:index])
                del self._buffer[:index]
                if plain:
                    self._hold_space.before_other_input()
                    self._emit(plain)
                continue

            if len(self._buffer) < 2:
                return
            if self._buffer[1] != ord("["):
                self._hold_space.before_other_input()
                self._emit(bytes(self._buffer[:2]))
                del self._buffer[:2]
                continue

            final_index = None
            for index in range(2, len(self._buffer)):
                if 0x40 <= self._buffer[index] <= 0x7E:
                    final_index = index
                    break
            if final_index is None:
                return

            sequence = bytes(self._buffer[: final_index + 1])
            del self._buffer[: final_index + 1]
            if sequence == BRACKETED_PASTE_START:
                self._hold_space.before_other_input()
                self._emit(sequence)
                self._in_paste = True
                continue
            self._handle_sequence(sequence, now)

    def _handle_sequence(self, sequence: bytes, now: float) -> None:
        match = self._CSI_U.match(sequence)
        if match is None:
            self._hold_space.before_other_input()
            self._emit(sequence)
            return

        body = match.group(1)
        if body.startswith(b"?"):
            # Hide the extra adapter-owned flags from Codex.
            try:
                flags = int(body[1:]) & ~0b11000
                self._emit(f"\x1b[?{flags}u".encode())
            except ValueError:
                self._emit(sequence)
            return

        fields = body.split(b";")
        try:
            key_code = int(fields[0].split(b":", 1)[0])
            modifiers_and_event = fields[1].split(b":") if len(fields) > 1 else [b"1"]
            modifier_value = int(modifiers_and_event[0] or b"1")
            event_type = int(modifiers_and_event[1]) if len(modifiers_and_event) > 1 else 1
        except ValueError:
            self._hold_space.before_other_input()
            self._emit(sequence)
            return

        actual_modifiers = max(0, modifier_value - 1)
        only_lock_modifiers = actual_modifiers & ~(0b11000000) == 0

        if key_code == 32 and only_lock_modifiers:
            if event_type == 1:
                self._hold_space.press(now)
            elif event_type == 2:
                self._hold_space.repeat(now)
            elif event_type == 3:
                self._hold_space.release(now)
            return

        self._hold_space.before_other_input()

        text_codepoints: list[int] = []
        if len(fields) > 2 and fields[2]:
            try:
                text_codepoints = [int(value) for value in fields[2].split(b":") if value]
            except ValueError:
                text_codepoints = []

        if event_type in (1, 2) and text_codepoints:
            try:
                self._emit("".join(chr(value) for value in text_codepoints).encode("utf-8"))
                self._text_keys_down.add(key_code)
                return
            except (ValueError, UnicodeEncodeError):
                pass

        legacy_controls = {9: b"\t", 13: b"\r", 127: b"\x7f"}
        if event_type in (1, 2) and only_lock_modifiers and key_code in legacy_controls:
            self._emit(legacy_controls[key_code])
            self._text_keys_down.add(key_code)
            return

        if event_type == 3 and key_code in self._text_keys_down:
            self._text_keys_down.discard(key_code)
            return

        # Codex requested flags 7, so remove the associated-text field that our
        # temporary flags 8+16 added.  Modified/function key CSI-u events remain.
        normalized = b"\x1b[" + b";".join(fields[:2]) + b"u"
        self._emit(normalized)


def _copy_window_size(source_fd: int, destination_fd: int) -> None:
    try:
        size = fcntl.ioctl(source_fd, termios.TIOCGWINSZ, b"\0" * 8)
        fcntl.ioctl(destination_fd, termios.TIOCSWINSZ, size)
    except OSError:
        pass


def _hold_threshold() -> float:
    raw = os.environ.get("AGENT_TWEAKS_HOLD_MS", os.environ.get("CODEX_PTT_HOLD_MS", "320"))
    try:
        milliseconds = int(raw)
    except ValueError:
        milliseconds = 320
    return max(150, min(milliseconds, 1000)) / 1000.0


def run(argv: list[str]) -> int:
    real_codex = _find_real_codex()
    if real_codex is None:
        print("codex-hold-to-dictate: could not find the real Codex executable on PATH", file=sys.stderr)
        return 127

    disabled = (
        os.environ.get("AGENT_TWEAKS_DISABLE") == "1"
        or os.environ.get("CODEX_DICTATION_DISABLE") == "1"
    )
    if disabled or not (os.isatty(sys.stdin.fileno()) and os.isatty(sys.stdout.fileno())):
        os.execv(real_codex, [real_codex, *argv])

    child_pid, master_fd = pty.fork()
    if child_pid == 0:
        os.execv(real_codex, [real_codex, *argv])

    stdin_fd = sys.stdin.fileno()
    stdout_fd = sys.stdout.fileno()
    original_termios = termios.tcgetattr(stdin_fd)
    keyboard_mode_enabled = False

    def send_to_codex(data: bytes) -> None:
        _write_all(master_fd, data)

    model_path = _default_model_path()
    dictation = DictationController(send_to_codex, model_path)
    hold_space = HoldSpace(
        send_to_codex,
        dictation.hold_started,
        dictation.hold_released,
        _hold_threshold(),
    )
    normalizer = InputNormalizer(send_to_codex, hold_space)

    def mode_enabled() -> None:
        nonlocal keyboard_mode_enabled
        keyboard_mode_enabled = True

    rewriter = OutputModeRewriter(mode_enabled)

    def resize(_signum: int | None = None, _frame: object | None = None) -> None:
        _copy_window_size(stdin_fd, master_fd)

    previous_winch = signal.signal(signal.SIGWINCH, resize)
    resize()
    tty_state = termios.tcgetattr(stdin_fd)
    tty_state[3] &= ~(termios.ECHO | termios.ICANON | termios.IEXTEN | termios.ISIG)
    tty_state[6][termios.VMIN] = 1
    tty_state[6][termios.VTIME] = 0
    termios.tcsetattr(stdin_fd, termios.TCSANOW, tty_state)

    child_finished = False
    child_status: int | None = None
    try:
        while not child_finished:
            now = time.monotonic()
            wait_for = hold_space.seconds_until_hold(now)
            timeout = min(wait_for if wait_for is not None else 0.25, 0.25)
            readable, _, _ = select.select([stdin_fd, master_fd], [], [], timeout)

            if master_fd in readable:
                try:
                    output = os.read(master_fd, 65536)
                except OSError as error:
                    if error.errno == errno.EIO:
                        output = b""
                    else:
                        raise
                if not output:
                    child_finished = True
                else:
                    transformed = rewriter.feed(output)
                    if transformed:
                        _write_all(stdout_fd, transformed)

            if stdin_fd in readable:
                user_input = os.read(stdin_fd, 65536)
                if not user_input:
                    child_finished = True
                elif keyboard_mode_enabled:
                    normalizer.feed(user_input, time.monotonic())
                else:
                    send_to_codex(user_input)

            now = time.monotonic()
            hold_space.check(now)

            waited_pid, status = os.waitpid(child_pid, os.WNOHANG)
            if waited_pid == child_pid:
                child_finished = True
                child_status = status
    finally:
        dictation.close()
        pending = rewriter.flush()
        if pending:
            _write_all(stdout_fd, pending)
        termios.tcsetattr(stdin_fd, termios.TCSADRAIN, original_termios)
        signal.signal(signal.SIGWINCH, previous_winch)
        try:
            os.close(master_fd)
        except OSError:
            pass

    if child_status is None:
        try:
            _, child_status = os.waitpid(child_pid, 0)
        except ChildProcessError:
            return 0
    return os.waitstatus_to_exitcode(child_status)


def main() -> None:
    raise SystemExit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
