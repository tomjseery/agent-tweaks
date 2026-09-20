from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest


SHARED_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_ROOT))

from session_restore_core import Session, load_manifest, resume_command, save_manifest


class ManifestTests(unittest.TestCase):
    def test_round_trip_is_private_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "last.json"
            first = Session("codex", "one", "/work", "Old", 1.0)
            newer = Session("codex", "one", "/work", "New", 2.0)
            claude = Session("claude", "two", "/other", "Claude", 1.0)

            save_manifest(path, [first, newer, claude])

            self.assertEqual(load_manifest(path), [claude, newer])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_invalid_entries_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "last.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "sessions": [
                            {"agent": "other", "session_id": "bad", "cwd": "/"},
                            {"agent": "codex", "session_id": "good", "cwd": "/work"},
                        ],
                    }
                )
            )

            self.assertEqual(
                load_manifest(path), [Session("codex", "good", "/work")]
            )

    def test_missing_or_unknown_manifest_is_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "last.json"
            self.assertEqual(load_manifest(path), [])
            path.write_text('{"version": 999, "sessions": []}')
            self.assertEqual(load_manifest(path), [])


class ResumeCommandTests(unittest.TestCase):
    def test_codex_command(self):
        session = Session("codex", "abc", "/work")
        self.assertEqual(resume_command(session), ["codex", "resume", "abc"])

    def test_claude_command(self):
        session = Session("claude", "abc", "/work")
        self.assertEqual(resume_command(session), ["claude", "--resume", "abc"])

    def test_display_name_is_safe_for_one_line_output(self):
        session = Session("codex", "abc", "/work", "  First\nsecond\x1b  ")
        self.assertEqual(session.display_name, "First second")


if __name__ == "__main__":
    unittest.main()
