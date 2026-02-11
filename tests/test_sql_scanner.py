"""Tests for SQL scanner."""

import tempfile
from pathlib import Path

from data_lineage_tool.sql_scanner import scan_directory


class TestScanDirectory:
    def test_finds_sql_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sql_file = Path(tmpdir) / "test.sql"
            sql_file.write_text("SELECT 1")
            results = scan_directory(Path(tmpdir))
            assert len(results) == 1
            assert results[0].relative_path == "test.sql"

    def test_skips_empty_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sql_file = Path(tmpdir) / "empty.sql"
            sql_file.write_text("   ")
            results = scan_directory(Path(tmpdir))
            assert len(results) == 0

    def test_skips_non_sql(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            txt_file = Path(tmpdir) / "readme.txt"
            txt_file.write_text("not sql")
            results = scan_directory(Path(tmpdir))
            assert len(results) == 0

    def test_recursive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            (subdir / "nested.sql").write_text("SELECT 1")
            results = scan_directory(Path(tmpdir))
            assert len(results) == 1
            assert "subdir/nested.sql" in results[0].relative_path

    def test_skips_git_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()
            (git_dir / "config.sql").write_text("SELECT 1")
            results = scan_directory(Path(tmpdir))
            assert len(results) == 0
