"""Policy clause index (SRS §3.1, P1).

Parses `data/trendly_policy.md` into addressable clauses — id (e.g. "2.3"),
title, verbatim body text — once at import time. `trendly_policy.md` is
never modified; this module only reads it (CURSOR_INSTRUCTIONS.md §6).

The system prompt (Phase 5) is given only `clause_index()` — id + title,
never the clause text — so every policy claim in a reply has to come from a
`search_policy()` call (see `policy_search.py`) and is therefore verifiable
from the trace (P1).

Split out of `search_policy()` (which lives in `policy_search.py`) to keep
each file under NFR-7's ~150-line limit — parsing and search are two
different jobs sharing one dataset.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

POLICY_PATH = Path(__file__).resolve().parent / "data" / "trendly_policy.md"

_SECTION_RE = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$")
_CLAUSE_RE = re.compile(r"^\*\*(\d+\.\d+)\s+(.+?)\.?\*\*\s*(.*)$")


@dataclass(frozen=True)
class Clause:
    id: str
    title: str
    section_id: str
    section_title: str
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "section_id": self.section_id,
            "section_title": self.section_title,
            "text": self.text,
        }


_clauses: Optional[list[Clause]] = None


def _sort_key(clause_id: str) -> tuple[int, int]:
    parts = clause_id.split(".")
    return (int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)


def _split_sections(lines: list[str]) -> list[tuple[str, str, list[str]]]:
    """Group raw lines into (section_id, section_title, body_lines) blocks,
    one per `## N. Title` header.
    """
    sections: list[tuple[str, str, list[str]]] = []
    current: Optional[list[Any]] = None
    for line in lines:
        match = _SECTION_RE.match(line)
        if match:
            if current is not None:
                sections.append((current[0], current[1], current[2]))
            current = [match.group(1), match.group(2), []]
        elif current is not None:
            current[2].append(line)
    if current is not None:
        sections.append((current[0], current[1], current[2]))
    return sections


def _clean_body(lines: list[str]) -> str:
    """Trim leading/trailing blank lines and a trailing `---` rule."""
    while lines and lines[0].strip() == "":
        lines.pop(0)
    while lines and lines[-1].strip() in ("", "---"):
        lines.pop()
    return "\n".join(lines).strip()


def _parse_section(section_id: str, section_title: str, body: list[str]) -> list[Clause]:
    """Split one section's body into its numbered clauses (e.g. `2.1`..`2.6`
    under section 2). A section with no numbered clauses (§7, bullets only)
    becomes a single section-level clause instead, so it stays searchable
    and citable.
    """
    header_idxs = [i for i, line in enumerate(body) if _CLAUSE_RE.match(line)]
    if not header_idxs:
        text = _clean_body(list(body))
        return [Clause(section_id, section_title, section_id, section_title, text)]

    clauses = []
    for pos, idx in enumerate(header_idxs):
        end = header_idxs[pos + 1] if pos + 1 < len(header_idxs) else len(body)
        match = _CLAUSE_RE.match(body[idx])
        assert match is not None
        clause_id, title, rest_of_line = match.group(1), match.group(2), match.group(3)
        chunk = [rest_of_line] + body[idx + 1 : end]
        text = _clean_body(chunk)
        clauses.append(Clause(clause_id, title, section_id, section_title, text))
    return clauses


def _parse_policy() -> list[Clause]:
    lines = POLICY_PATH.read_text(encoding="utf-8").splitlines()
    clauses: list[Clause] = []
    for section_id, section_title, body in _split_sections(lines):
        clauses.extend(_parse_section(section_id, section_title, body))
    clauses.sort(key=lambda c: _sort_key(c.id))
    return clauses


def get_clauses(force_reload: bool = False) -> list[Clause]:
    """All parsed clauses, cached after first parse."""
    global _clauses
    if _clauses is None or force_reload:
        _clauses = _parse_policy()
    return _clauses


def get_clause(clause_id: str) -> Optional[dict[str, Any]]:
    """Direct lookup by clause id (e.g. "2.3") — the re-query path P7
    depends on once a keyword search comes back weak.
    """
    for clause in get_clauses():
        if clause.id == clause_id:
            return clause.to_dict()
    return None


def clause_index() -> list[dict[str, str]]:
    """The id+title index only — never clause text. This is what the system
    prompt is given (P1); text must always come from `search_policy()`.
    """
    return [{"id": c.id, "title": c.title} for c in get_clauses()]
