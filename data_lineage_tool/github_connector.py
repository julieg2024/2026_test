"""GitHub repository connector: clone repos or resolve local paths."""

import tempfile
from pathlib import Path

from git import Repo


def clone_repo(
    repo_url: str,
    target_dir: str | None = None,
    branch: str | None = None,
) -> Path:
    """Clone a GitHub repo (shallow). Returns path to cloned directory."""
    if target_dir is None:
        target_dir = tempfile.mkdtemp(prefix="lineage_")

    clone_kwargs = {"depth": 1}
    if branch:
        clone_kwargs["branch"] = branch

    Repo.clone_from(repo_url, target_dir, **clone_kwargs)
    return Path(target_dir)


def resolve_source(source: str, branch: str | None = None) -> Path:
    """
    Accept a GitHub URL or local directory path.
    If URL, clones it. If local path, validates and returns it.
    """
    if source.startswith(("http://", "https://", "git@")):
        return clone_repo(source, branch=branch)

    path = Path(source)
    if not path.is_dir():
        raise FileNotFoundError(f"Directory not found: {source}")
    return path
