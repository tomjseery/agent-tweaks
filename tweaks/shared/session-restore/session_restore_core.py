"""Platform-neutral manifest helpers for Session Restore."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


MANIFEST_VERSION = 1
SUPPORTED_AGENTS = frozenset({"codex", "claude"})


@dataclass(frozen=True, slots=True)
class Session:
    """A resumable interactive agent session."""

    agent: str
    session_id: str
    cwd: str
    name: str = ""
    updated_at: float = 0.0

    @classmethod
    def from_dict(cls, value: object) -> "Session | None":
        if not isinstance(value, dict):
            return None
        agent = value.get("agent")
        session_id = value.get("session_id")
        cwd = value.get("cwd")
        if agent not in SUPPORTED_AGENTS or not all(
            isinstance(item, str) and item for item in (session_id, cwd)
        ):
            return None
        name = value.get("name", "")
        updated_at = value.get("updated_at", 0.0)
        return cls(
            agent=agent,
            session_id=session_id,
            cwd=cwd,
            name=name if isinstance(name, str) else "",
            updated_at=float(updated_at) if isinstance(updated_at, (int, float)) else 0.0,
        )

    @property
    def key(self) -> tuple[str, str]:
        return self.agent, self.session_id

    @property
    def display_name(self) -> str:
        # Names originate in local session metadata and can contain newlines or
        # control characters from the first prompt. Keep terminal titles and
        # command output on one safe, readable line.
        printable = "".join(
            character if character.isprintable() else " " for character in self.name
        )
        return " ".join(printable.split()) or self.session_id[:8]


def unique_sessions(sessions: Iterable[Session]) -> list[Session]:
    """Deduplicate sessions and return a stable, user-facing order."""

    by_key: dict[tuple[str, str], Session] = {}
    for session in sessions:
        existing = by_key.get(session.key)
        if existing is None or session.updated_at >= existing.updated_at:
            by_key[session.key] = session
    return sorted(
        by_key.values(),
        key=lambda item: (item.agent, item.cwd.casefold(), item.display_name.casefold()),
    )


def save_manifest(path: Path, sessions: Iterable[Session]) -> None:
    """Atomically save a private manifest."""

    normalized = unique_sessions(sessions)
    payload = {
        "version": MANIFEST_VERSION,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "sessions": [asdict(session) for session in normalized],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
        temporary.chmod(0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_manifest(path: Path) -> list[Session]:
    """Load valid sessions from a manifest, ignoring malformed entries."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict) or payload.get("version") != MANIFEST_VERSION:
        return []
    raw_sessions = payload.get("sessions")
    if not isinstance(raw_sessions, list):
        return []
    sessions = (Session.from_dict(value) for value in raw_sessions)
    return unique_sessions(session for session in sessions if session is not None)


def resume_command(session: Session) -> list[str]:
    """Return the agent command used to resume one exact session."""

    if session.agent == "codex":
        return ["codex", "resume", session.session_id]
    if session.agent == "claude":
        return ["claude", "--resume", session.session_id]
    raise ValueError(f"unsupported agent: {session.agent}")
