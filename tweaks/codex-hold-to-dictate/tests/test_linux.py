from __future__ import annotations

import pathlib
import sys
import unittest


TWEAK_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TWEAK_ROOT))
sys.path.insert(0, str(TWEAK_ROOT / "linux"))

from codex_hold_to_dictate import InputNormalizer, OutputModeRewriter
from dictation_core import HoldSpace, vosk_text


class HoldSpaceTests(unittest.TestCase):
    def make_filter(self):
        emitted: list[bytes] = []
        events: list[str] = []
        hold = HoldSpace(
            emitted.append,
            lambda: events.append("hold"),
            lambda: events.append("release"),
            0.3,
        )
        return hold, emitted, events

    def test_tap_remains_a_normal_space(self):
        hold, emitted, events = self.make_filter()
        hold.press(1.0)
        hold.release(1.1)
        self.assertEqual(emitted, [b" "])
        self.assertEqual(events, [])

    def test_hold_fires_on_threshold_and_release(self):
        hold, emitted, events = self.make_filter()
        hold.press(1.0)
        hold.check(1.31)
        hold.release(1.5)
        self.assertEqual(emitted, [])
        self.assertEqual(events, ["hold", "release"])

    def test_rolling_typing_preserves_space_before_next_character(self):
        hold, emitted, events = self.make_filter()
        hold.press(1.0)
        hold.before_other_input()
        emitted.append(b"a")
        hold.release(1.1)
        self.assertEqual(emitted, [b" ", b"a"])
        self.assertEqual(events, [])


class InputNormalizerTests(unittest.TestCase):
    def make_normalizer(self):
        emitted: list[bytes] = []
        events: list[str] = []
        hold = HoldSpace(
            emitted.append,
            lambda: events.append("hold"),
            lambda: events.append("release"),
            0.3,
        )
        return InputNormalizer(emitted.append, hold), hold, emitted, events

    def test_space_press_and_split_release_become_hold(self):
        normalizer, hold, emitted, events = self.make_normalizer()
        normalizer.feed(b"\x1b[32;1:1;32u", 1.0)
        hold.check(1.31)
        normalizer.feed(b"\x1b[32;1", 1.4)
        normalizer.feed(b":3u", 1.4)
        self.assertEqual(emitted, [])
        self.assertEqual(events, ["hold", "release"])

    def test_text_keys_are_converted_back_to_utf8(self):
        normalizer, _, emitted, _ = self.make_normalizer()
        normalizer.feed(b"\x1b[97;1:1;97u\x1b[97;1:3u", 1.0)
        normalizer.feed(b"\x1b[97:65;2:1;65u\x1b[97:65;1:3u", 1.1)
        self.assertEqual(emitted, [b"a", b"A"])

    def test_paste_spaces_are_not_intercepted(self):
        normalizer, _, emitted, events = self.make_normalizer()
        normalizer.feed(b"\x1b[200~hello world\x1b[201~", 1.0)
        self.assertEqual(b"".join(emitted), b"\x1b[200~hello world\x1b[201~")
        self.assertEqual(events, [])

    def test_terminal_mode_reply_is_hidden_from_codex(self):
        normalizer, _, emitted, _ = self.make_normalizer()
        normalizer.feed(b"\x1b[?31u", 1.0)
        self.assertEqual(emitted, [b"\x1b[?7u"])


class OutputModeRewriterTests(unittest.TestCase):
    def test_mode_request_is_rewritten_across_chunks(self):
        enabled: list[bool] = []
        rewriter = OutputModeRewriter(lambda: enabled.append(True))
        first = rewriter.feed(b"before\x1b[>")
        second = rewriter.feed(b"7uafter")
        self.assertEqual(first + second, b"before\x1b[>31uafter")
        self.assertEqual(enabled, [True])


class VoskResultTests(unittest.TestCase):
    def test_extracts_and_normalizes_transcript(self):
        self.assertEqual(vosk_text('{"text": " hello   world "}'), "hello world")

    def test_invalid_result_is_empty(self):
        self.assertEqual(vosk_text("not-json"), "")


if __name__ == "__main__":
    unittest.main()
