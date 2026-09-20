#!/usr/bin/env python3
"""Silently track and restore live Codex and Claude CLI sessions on Linux."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import shlex
import shutil
import signal
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path


SHARED_ROOT = Path(__file__).resolve().parents[2] / "shared" / "session-restore"
if (SHARED_ROOT / "session_restore_core.py").is_file():
    sys.path.insert(0, str(SHARED_ROOT))
else:
    # The installer places the platform entry point and shared core together.
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from session_restore_core import Session, load_manifest, resume_command, save_manifest


POLL_SECONDS = 3.0


def _home() -> Path:
    return Path.home()


def _state_dir() -> Path:
    state_home = Path(os.environ.get("XDG_STATE_HOME", _home() / ".local/state"))
    return state_home / "agent-tweaks" / "session-restore"


def _current_manifest() -> Path:
    return _state_dir() / "current.json"


def _last_manifest() -> Path:
    return _state_dir() / "last.json"


def _lock_is_held(path: Path) -> bool:
    """Return whether another process holds an advisory lock on path."""

    try:
        with path.open("rb") as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return True
            fcntl.flock(stream, fcntl.LOCK_UN)
    except OSError:
        return False
    return False


def _codex_database() -> Path | None:
    codex_home = Path(os.environ.get("CODEX_HOME", _home() / ".codex"))
    candidates = list(codex_home.glob("state_*.sqlite"))
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _codex_metadata(session_ids: set[str]) -> dict[str, tuple[str, str, float]]:
    """Return metadata for top-level Codex CLI sessions only.

    Codex uses the writer-lock directory for both user sessions and internal
    workers such as guardian reviews. The database source fields distinguish
    those internal workers from resumable user sessions.
    """

    database = _codex_database()
    if database is None or not session_ids:
        return {}
    try:
        connection = sqlite3.connect(
            f"file:{database}?mode=ro", uri=True, timeout=0.2
        )
        try:
            columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(threads)")
            }
            if not {"id", "cwd", "source"}.issubset(columns):
                return {}

            name_parts = []
            if "name" in columns:
                name_parts.append("NULLIF(name, '')")
            if "title" in columns:
                name_parts.append("NULLIF(title, '')")
            name_parts.append("id")
            name_expression = f"COALESCE({', '.join(name_parts)})"

            if "updated_at_ms" in columns and "updated_at" in columns:
                updated_expression = "COALESCE(updated_at_ms / 1000.0, updated_at)"
            elif "updated_at_ms" in columns:
                updated_expression = "updated_at_ms / 1000.0"
            elif "updated_at" in columns:
                updated_expression = "updated_at"
            else:
                updated_expression = "0.0"

            placeholders = ",".join("?" for _ in session_ids)
            filters = [f"id IN ({placeholders})", "source = 'cli'"]
            if "thread_source" in columns:
                filters.append("(thread_source = 'user' OR thread_source IS NULL)")
            query = f"""
                SELECT id, cwd, {name_expression}, {updated_expression}
                FROM threads
                WHERE {' AND '.join(filters)}
            """
            rows = connection.execute(query, tuple(session_ids)).fetchall()
        finally:
            connection.close()
    except (OSError, sqlite3.Error):
        return {}
    return {
        str(session_id): (str(cwd), str(name), float(updated_at or 0.0))
        for session_id, cwd, name, updated_at in rows
    }


def _active_codex_ids() -> set[str]:
    codex_home = Path(os.environ.get("CODEX_HOME", _home() / ".codex"))
    lock_dir = codex_home / "thread-writer-locks"
    return {
        path.stem
        for path in lock_dir.glob("*.lock")
        if path.name != ".coordination.lock" and _lock_is_held(path)
    }


def scan_codex_sessions() -> list[Session]:
    """Find live top-level Codex sessions through Codex's writer locks."""

    active_ids = _active_codex_ids()
    metadata = _codex_metadata(active_ids)
    sessions: list[Session] = []
    for session_id, (cwd, name, updated_at) in metadata.items():
        sessions.append(
            Session(
                agent="codex",
                session_id=session_id,
                cwd=cwd,
                name=name,
                updated_at=updated_at,
            )
        )
    return sessions


def _linux_process_start(pid: int) -> str | None:
    try:
        content = (Path("/proc") / str(pid) / "stat").read_text(encoding="utf-8")
        # The command name is parenthesized and may contain spaces. Fields after
        # it start at process-stat field 3; starttime is field 22.
        fields_after_name = content[content.rfind(")") + 2 :].split()
        return fields_after_name[19]
    except (IndexError, OSError):
        return None


def _claude_process_is_live(pid: int, expected_start: object) -> bool:
    actual_start = _linux_process_start(pid)
    if actual_start is None:
        return False
    return expected_start is None or str(expected_start) == actual_start


def scan_claude_sessions() -> list[Session]:
    """Find live Claude sessions through Claude's local session registry."""

    registry = _home() / ".claude" / "sessions"
    sessions: list[Session] = []
    for path in registry.glob("*.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            pid = int(value["pid"])
            session_id = value["sessionId"]
            cwd = value["cwd"]
        except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
            continue
        if not all(isinstance(item, str) and item for item in (session_id, cwd)):
            continue
        if not _claude_process_is_live(pid, value.get("procStart")):
            continue
        name = value.get("name")
        updated_at = value.get("updatedAt", 0)
        sessions.append(
            Session(
                agent="claude",
                session_id=session_id,
                cwd=cwd,
                name=name if isinstance(name, str) else "",
                updated_at=float(updated_at) / 1000.0
                if isinstance(updated_at, (int, float))
                else 0.0,
            )
        )
    return sessions


def scan_sessions() -> list[Session]:
    return [*scan_codex_sessions(), *scan_claude_sessions()]


def snapshot(*, quiet: bool = False) -> list[Session]:
    sessions = scan_sessions()
    save_manifest(_current_manifest(), sessions)
    # Preserve the last useful workspace when shutdown makes the active set
    # empty. This also makes unexpected power loss recoverable.
    if sessions:
        save_manifest(_last_manifest(), sessions)
    if not quiet:
        print(f"Saved {len(sessions)} active session(s).")
    return sessions


def watch(interval: float) -> int:
    stop = threading.Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stop.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    previous: tuple[tuple[str, str, str, str], ...] | None = None
    while not stop.is_set():
        sessions = scan_sessions()
        fingerprint = tuple(
            sorted((item.agent, item.session_id, item.cwd, item.name) for item in sessions)
        )
        if fingerprint != previous:
            save_manifest(_current_manifest(), sessions)
            if sessions:
                save_manifest(_last_manifest(), sessions)
            previous = fingerprint
        stop.wait(interval)
    return 0


def _abbreviate(value: str, width: int) -> str:
    if len(value) <= width:
        return value
    return f"{value[: width - 1]}…"


def _print_sessions(
    sessions: list[Session], *, empty_message: str = "No saved sessions."
) -> None:
    if not sessions:
        print(empty_message)
        return
    for index, session in enumerate(sessions, start=1):
        name = _abbreviate(session.display_name, 40)
        print(
            f"{index:>2}. {session.agent:<6}  {name:<40}  {session.cwd}"
        )


def _terminal() -> str | None:
    override = os.environ.get("SESSION_RESTORE_TERMINAL")
    if override:
        return shutil.which(override) or override
    for candidate in ("konsole", "kitty", "x-terminal-emulator"):
        executable = shutil.which(candidate)
        if executable:
            return executable
    return None


def _launch_in_terminal(
    terminal: str, session: Session, *, new_tab: bool
) -> None:
    cwd = Path(session.cwd).expanduser()
    if not cwd.is_dir():
        raise FileNotFoundError(f"working directory no longer exists: {cwd}")
    shell = os.environ.get("SHELL") or shutil.which("bash") or "/bin/sh"
    agent_command = shlex.join(resume_command(session))
    shell_command = f"{agent_command}; exec {shlex.quote(shell)}"
    title = f"{session.agent.title()}: {_abbreviate(session.display_name, 64)}"
    terminal_name = Path(terminal).name

    if terminal_name == "konsole":
        command = [terminal]
        if new_tab:
            command.append("--new-tab")
        command.extend(
            [
                "--workdir",
                str(cwd),
                "-p",
                f"tabtitle={title}",
                "-e",
                shell,
                "-ic",
                shell_command,
            ]
        )
    elif terminal_name == "kitty":
        command = [
            terminal,
            "--directory",
            str(cwd),
            "--title",
            title,
            shell,
            "-ic",
            shell_command,
        ]
    else:
        command = [terminal, "-e", shell, "-ic", shell_command]

    subprocess.Popen(
        command,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _notify(message: str) -> None:
    executable = shutil.which("notify-send")
    if executable is None:
        return
    subprocess.Popen(
        [executable, "Session Restore", message],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def restore(*, dry_run: bool, gui: bool) -> int:
    saved = load_manifest(_last_manifest())
    if not saved:
        message = "No saved sessions were found."
        print(message)
        if gui:
            _notify(message)
        return 0

    active_keys = {session.key for session in scan_sessions()}
    # Treat any held Codex session ID as active when comparing against an
    # already-filtered manifest. This avoids opening a duplicate if a brief
    # SQLite read failure prevents its metadata from being returned.
    active_keys.update(("codex", session_id) for session_id in _active_codex_ids())
    pending = [session for session in saved if session.key not in active_keys]
    if dry_run:
        _print_sessions(
            pending,
            empty_message="No closed saved sessions need restoring.",
        )
        return 0
    if not pending:
        message = "All saved sessions are already open."
        print(message)
        if gui:
            _notify(message)
        return 0

    terminal = _terminal()
    if terminal is None:
        print("session-restore: no supported terminal was found", file=sys.stderr)
        return 1

    restored = 0
    errors: list[str] = []
    for session in pending:
        try:
            _launch_in_terminal(terminal, session, new_tab=restored > 0)
        except (OSError, ValueError) as error:
            errors.append(f"{session.agent} {session.display_name}: {error}")
            continue
        restored += 1
        time.sleep(0.25)

    print(f"Restored {restored} session(s).")
    for error in errors:
        print(f"warning: {error}", file=sys.stderr)
    if gui:
        _notify(f"Restored {restored} session(s).")
    return 1 if errors else 0


def clear() -> int:
    _current_manifest().unlink(missing_ok=True)
    _last_manifest().unlink(missing_ok=True)
    print("Cleared saved sessions.")
    return 0


def doctor() -> int:
    print(f"State directory: {_state_dir()}")
    print(f"Terminal: {_terminal() or 'not found'}")
    print(f"Active sessions: {len(scan_sessions())}")
    print(f"Saved sessions: {len(load_manifest(_last_manifest()))}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="session-restore",
        description="Track and restore Codex and Claude CLI sessions.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    watch_parser = subparsers.add_parser("watch", help="run the silent tracker")
    watch_parser.add_argument("--interval", type=float, default=POLL_SECONDS)
    subparsers.add_parser("snapshot", help="save the currently open sessions")
    subparsers.add_parser("list", help="list the last saved sessions")
    restore_parser = subparsers.add_parser("restore", help="restore saved sessions")
    restore_parser.add_argument("--dry-run", action="store_true")
    restore_parser.add_argument("--gui", action="store_true", help=argparse.SUPPRESS)
    subparsers.add_parser("clear", help="forget the saved workspace")
    subparsers.add_parser("doctor", help="show tracker diagnostics")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.command == "watch":
        return watch(max(1.0, arguments.interval))
    if arguments.command == "snapshot":
        snapshot()
        return 0
    if arguments.command == "list":
        _print_sessions(load_manifest(_last_manifest()))
        return 0
    if arguments.command == "restore":
        return restore(dry_run=arguments.dry_run, gui=arguments.gui)
    if arguments.command == "clear":
        return clear()
    if arguments.command == "doctor":
        return doctor()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
