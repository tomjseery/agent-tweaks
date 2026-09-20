"""Platform-neutral state and transcript helpers for hold-to-dictate."""

from __future__ import annotations

import json
from collections.abc import Callable


VOSK_MODEL_NAME = "vosk-model-small-en-us-0.15"


def vosk_text(payload: str) -> str:
    """Return normalized transcript text from a Vosk JSON result."""

    try:
        value = json.loads(payload).get("text", "")
    except (AttributeError, json.JSONDecodeError):
        return ""
    return " ".join(str(value).split())


class HoldSpace:
    """Distinguish a tap from a hold while preserving normal typing order."""

    def __init__(
        self,
        emit: Callable[[bytes], None],
        on_hold: Callable[[], None],
        on_release: Callable[[], None],
        threshold_seconds: float,
    ) -> None:
        self._emit = emit
        self._on_hold = on_hold
        self._on_release = on_release
        self.threshold_seconds = threshold_seconds
        self.down_since: float | None = None
        self.holding = False
        self.passed_through = False

    def press(self, now: float) -> None:
        if self.down_since is None:
            self.down_since = now
            self.holding = False
            self.passed_through = False

    def repeat(self, now: float) -> None:
        self.check(now)

    def release(self, now: float) -> None:
        if self.down_since is None:
            return
        self.check(now)
        if self.holding:
            self._on_release()
        elif not self.passed_through:
            self._emit(b" ")
        self.down_since = None
        self.holding = False
        self.passed_through = False

    def before_other_input(self) -> None:
        # Preserve the original typing order when Space rolls into a letter.
        if self.down_since is not None and not self.holding and not self.passed_through:
            self._emit(b" ")
            self.passed_through = True

    def check(self, now: float) -> None:
        if (
            self.down_since is not None
            and not self.holding
            and not self.passed_through
            and now - self.down_since >= self.threshold_seconds
        ):
            self.holding = True
            self._on_hold()

    def seconds_until_hold(self, now: float) -> float | None:
        if self.down_since is None or self.holding or self.passed_through:
            return None
        return max(0.0, self.threshold_seconds - (now - self.down_since))
