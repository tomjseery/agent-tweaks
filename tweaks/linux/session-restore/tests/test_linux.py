from __future__ import annotations

import fcntl
import json
import os
import pathlib
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock


LINUX_ROOT = pathlib.Path(__file__).resolve().parents[1]
SHARED_ROOT = pathlib.Path(__file__).resolve().parents[3] / "shared" / "session-restore"
sys.path.insert(0, str(LINUX_ROOT))
sys.path.insert(0, str(SHARED_ROOT))

import session_restore


class CodexDiscoveryTests(unittest.TestCase):
    def test_locked_codex_session_is_discovered(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            codex_home = root / ".codex"
            lock_dir = codex_home / "thread-writer-locks"
            lock_dir.mkdir(parents=True)
            lock_path = lock_dir / "session-123.lock"
            lock_path.touch()
            database = codex_home / "state_5.sqlite"
            connection = sqlite3.connect(database)
            connection.execute(
                "CREATE TABLE threads "
                "(id TEXT, cwd TEXT, name TEXT, title TEXT, "
                "updated_at_ms INTEGER, updated_at INTEGER, "
                "source TEXT, thread_source TEXT)"
            )
            connection.execute(
                "INSERT INTO threads VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "session-123",
                    "/work/project",
                    "Feature",
                    "",
                    2500,
                    2,
                    "cli",
                    "user",
                ),
            )
            connection.commit()
            connection.close()

            with lock_path.open("rb") as held_lock:
                fcntl.flock(held_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with mock.patch.dict(os.environ, {"CODEX_HOME": str(codex_home)}):
                    sessions = session_restore.scan_codex_sessions()

            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0].session_id, "session-123")
            self.assertEqual(sessions[0].cwd, "/work/project")
            self.assertEqual(sessions[0].name, "Feature")

    def test_internal_codex_session_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            codex_home = root / ".codex"
            lock_dir = codex_home / "thread-writer-locks"
            lock_dir.mkdir(parents=True)
            lock_path = lock_dir / "guardian-123.lock"
            lock_path.touch()
            database = codex_home / "state_5.sqlite"
            connection = sqlite3.connect(database)
            connection.execute(
                "CREATE TABLE threads "
                "(id TEXT, cwd TEXT, title TEXT, updated_at INTEGER, "
                "source TEXT, thread_source TEXT)"
            )
            connection.execute(
                "INSERT INTO threads VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "guardian-123",
                    "/work/project",
                    "Internal review",
                    2,
                    '{"subagent":{"other":"guardian"}}',
                    "guardian_review",
                ),
            )
            connection.commit()
            connection.close()

            with lock_path.open("rb") as held_lock:
                fcntl.flock(held_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with mock.patch.dict(os.environ, {"CODEX_HOME": str(codex_home)}):
                    sessions = session_restore.scan_codex_sessions()

            self.assertEqual(sessions, [])

    def test_locked_session_without_safe_metadata_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            codex_home = pathlib.Path(directory) / ".codex"
            lock_dir = codex_home / "thread-writer-locks"
            lock_dir.mkdir(parents=True)
            lock_path = lock_dir / "unknown.lock"
            lock_path.touch()

            with lock_path.open("rb") as held_lock:
                fcntl.flock(held_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with mock.patch.dict(os.environ, {"CODEX_HOME": str(codex_home)}):
                    sessions = session_restore.scan_codex_sessions()

            self.assertEqual(sessions, [])

    def test_unlocked_codex_session_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            codex_home = pathlib.Path(directory) / ".codex"
            lock_dir = codex_home / "thread-writer-locks"
            lock_dir.mkdir(parents=True)
            (lock_dir / "stale.lock").touch()

            with mock.patch.dict(os.environ, {"CODEX_HOME": str(codex_home)}):
                self.assertEqual(session_restore.scan_codex_sessions(), [])

    def test_active_ids_still_work_when_metadata_is_temporarily_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            codex_home = pathlib.Path(directory) / ".codex"
            lock_dir = codex_home / "thread-writer-locks"
            lock_dir.mkdir(parents=True)
            lock_path = lock_dir / "session-123.lock"
            lock_path.touch()

            with lock_path.open("rb") as held_lock:
                fcntl.flock(held_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with mock.patch.dict(os.environ, {"CODEX_HOME": str(codex_home)}):
                    self.assertEqual(
                        session_restore._active_codex_ids(), {"session-123"}
                    )


class ClaudeDiscoveryTests(unittest.TestCase):
    def test_live_registry_entry_is_discovered(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            registry = home / ".claude" / "sessions"
            registry.mkdir(parents=True)
            pid = os.getpid()
            process_start = session_restore._linux_process_start(pid)
            (registry / "42.json").write_text(
                json.dumps(
                    {
                        "pid": pid,
                        "procStart": process_start,
                        "sessionId": "claude-123",
                        "cwd": "/work/project",
                        "name": "Refactor",
                        "updatedAt": 5000,
                    }
                )
            )

            with mock.patch.object(session_restore, "_home", return_value=home):
                sessions = session_restore.scan_claude_sessions()

            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0].session_id, "claude-123")
            self.assertEqual(sessions[0].name, "Refactor")

    def test_stale_registry_entry_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            registry = home / ".claude" / "sessions"
            registry.mkdir(parents=True)
            (registry / "42.json").write_text(
                '{"pid":42,"sessionId":"old","cwd":"/work"}'
            )

            with (
                mock.patch.object(session_restore, "_home", return_value=home),
                mock.patch.object(
                    session_restore, "_claude_process_is_live", return_value=False
                ),
            ):
                self.assertEqual(session_restore.scan_claude_sessions(), [])


class ProcessTests(unittest.TestCase):
    def test_reads_current_process_start_time(self):
        self.assertIsNotNone(session_restore._linux_process_start(os.getpid()))


class OutputTests(unittest.TestCase):
    def test_abbreviate_keeps_output_bounded(self):
        self.assertEqual(session_restore._abbreviate("short", 10), "short")
        self.assertEqual(session_restore._abbreviate("abcdefghij", 6), "abcde…")


class TerminalLaunchTests(unittest.TestCase):
    def test_konsole_launch_uses_working_directory_and_exact_session(self):
        session = session_restore.Session(
            agent="codex",
            session_id="session-123",
            cwd="/work/project",
            name="Feature",
        )

        with (
            mock.patch.object(pathlib.Path, "is_dir", return_value=True),
            mock.patch.object(session_restore.subprocess, "Popen") as popen,
            mock.patch.dict(os.environ, {"SHELL": "/bin/bash"}),
        ):
            session_restore._launch_in_terminal(
                "/usr/bin/konsole", session, new_tab=True
            )

        command = popen.call_args.args[0]
        self.assertEqual(command[0:2], ["/usr/bin/konsole", "--new-tab"])
        self.assertIn("/work/project", command)
        self.assertTrue(
            any(
                argument.startswith("codex resume session-123;")
                for argument in command
            )
        )
        self.assertEqual(popen.call_args.kwargs["cwd"], pathlib.Path("/work/project"))


if __name__ == "__main__":
    unittest.main()
