"""Scan directories for SQL files."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class SQLFile:
    """A discovered SQL file with its content."""
    path: Path
    relative_path: str
    content: str


SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "env", ".tox"}


def scan_directory(
    root: Path,
    extensions: tuple[str, ...] = (".sql",),
) -> list[SQLFile]:
    """Recursively find all SQL files under root directory."""
    root = Path(root)
    results = []

    for path in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in extensions:
            content = path.read_text(encoding="utf-8", errors="replace")
            if content.strip():
                results.append(SQLFile(
                    path=path,
                    relative_path=str(path.relative_to(root)),
                    content=content,
                ))

    return results
