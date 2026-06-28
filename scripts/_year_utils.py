"""Shared year inference for PhilGEPS file paths."""

from __future__ import annotations

import re
from pathlib import Path

_YEAR_RE = re.compile(r"(20\d{2})")


def infer_year_from_name(filename: str) -> str | None:
    match = _YEAR_RE.search(filename)
    return match.group(1) if match else None


def year_from_path(path: Path) -> str | None:
    return infer_year_from_name(path.stem) or infer_year_from_name(path.parent.name)
