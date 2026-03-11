"""Tests for JSON file-based persistence layer."""

from __future__ import annotations

import json
import os
import threading
from typing import Any

import pytest

from src.utils.storage import JsonStorage


class TestSaveAndLoad:
    """Verify atomic save and load operations."""

    def test_save_creates_file(self, tmp_path: Any) -> None:
        filepath = str(tmp_path / "test.json")
        JsonStorage.save(filepath, {"key": "value"})
        assert os.path.exists(filepath)

    def test_save_writes_valid_json(self, tmp_path: Any) -> None:
        filepath = str(tmp_path / "test.json")
        data = {"name": "bot", "version": 1, "nested": {"a": [1, 2, 3]}}
        JsonStorage.save(filepath, data)
        with open(filepath) as f:
            loaded = json.load(f)
        assert loaded == data

    def test_load_returns_data(self, tmp_path: Any) -> None:
        filepath = str(tmp_path / "test.json")
        data = {"trades": [1, 2, 3]}
        JsonStorage.save(filepath, data)
        result = JsonStorage.load(filepath)
        assert result == data

    def test_load_returns_none_for_missing_file(self, tmp_path: Any) -> None:
        filepath = str(tmp_path / "nonexistent.json")
        result = JsonStorage.load(filepath)
        assert result is None

    def test_save_overwrites_existing(self, tmp_path: Any) -> None:
        filepath = str(tmp_path / "test.json")
        JsonStorage.save(filepath, {"v": 1})
        JsonStorage.save(filepath, {"v": 2})
        result = JsonStorage.load(filepath)
        assert result == {"v": 2}


class TestAtomicWrite:
    """Verify writes are atomic (temp file + rename)."""

    def test_no_partial_write_on_failure(self, tmp_path: Any) -> None:
        filepath = str(tmp_path / "atomic.json")
        JsonStorage.save(filepath, {"original": True})

        # Try to save non-serializable data — should fail
        class NotSerializable:
            pass

        with pytest.raises(TypeError):
            JsonStorage.save(filepath, {"bad": NotSerializable()})

        # Original file should still be intact
        result = JsonStorage.load(filepath)
        assert result == {"original": True}

    def test_no_temp_files_left_on_success(self, tmp_path: Any) -> None:
        filepath = str(tmp_path / "clean.json")
        JsonStorage.save(filepath, {"clean": True})
        files = os.listdir(tmp_path)
        assert len(files) == 1
        assert files[0] == "clean.json"


class TestBackup:
    """Verify backup creates timestamped copies."""

    def test_backup_creates_file(self, tmp_path: Any) -> None:
        filepath = str(tmp_path / "data.json")
        backup_dir = str(tmp_path / "backups")
        JsonStorage.save(filepath, {"state": "active"})

        backup_path = JsonStorage.backup(filepath, backup_dir=backup_dir)
        assert backup_path is not None
        assert os.path.exists(backup_path)

    def test_backup_content_matches_original(self, tmp_path: Any) -> None:
        filepath = str(tmp_path / "data.json")
        backup_dir = str(tmp_path / "backups")
        data = {"trades": [{"id": 1}, {"id": 2}]}
        JsonStorage.save(filepath, data)

        backup_path = JsonStorage.backup(filepath, backup_dir=backup_dir)
        assert backup_path is not None
        with open(backup_path) as f:
            backup_data = json.load(f)
        assert backup_data == data

    def test_backup_returns_none_for_missing_file(self, tmp_path: Any) -> None:
        filepath = str(tmp_path / "missing.json")
        result = JsonStorage.backup(filepath, backup_dir=str(tmp_path / "backups"))
        assert result is None

    def test_backup_creates_backup_dir(self, tmp_path: Any) -> None:
        filepath = str(tmp_path / "data.json")
        backup_dir = str(tmp_path / "deep" / "nested" / "backups")
        JsonStorage.save(filepath, {"ok": True})
        JsonStorage.backup(filepath, backup_dir=backup_dir)
        assert os.path.isdir(backup_dir)

    def test_backup_filename_contains_timestamp(self, tmp_path: Any) -> None:
        filepath = str(tmp_path / "data.json")
        backup_dir = str(tmp_path / "backups")
        JsonStorage.save(filepath, {})
        backup_path = JsonStorage.backup(filepath, backup_dir=backup_dir)
        assert backup_path is not None
        basename = os.path.basename(backup_path)
        assert basename.startswith("data_")
        assert basename.endswith(".json")


class TestRestore:
    """Verify restore from backup."""

    def test_restore_copies_backup_to_target(self, tmp_path: Any) -> None:
        filepath = str(tmp_path / "data.json")
        backup_dir = str(tmp_path / "backups")
        data = {"state": "original"}
        JsonStorage.save(filepath, data)
        backup_path = JsonStorage.backup(filepath, backup_dir=backup_dir)
        assert backup_path is not None

        # Overwrite original
        JsonStorage.save(filepath, {"state": "corrupted"})

        # Restore
        JsonStorage.restore(backup_path, filepath)
        result = JsonStorage.load(filepath)
        assert result == data


class TestThreadSafety:
    """Verify concurrent saves don't corrupt data."""

    def test_concurrent_saves(self, tmp_path: Any) -> None:
        filepath = str(tmp_path / "concurrent.json")
        errors: list[Exception] = []
        iterations = 50

        def writer(thread_id: int) -> None:
            try:
                for i in range(iterations):
                    JsonStorage.save(filepath, {"thread": thread_id, "iteration": i})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors during concurrent writes: {errors}"

        # File should be valid JSON with last write winning
        result = JsonStorage.load(filepath)
        assert result is not None
        assert "thread" in result
        assert "iteration" in result


class TestAutoCreateDirectory:
    """Verify data directory is auto-created if missing."""

    def test_save_creates_parent_dirs(self, tmp_path: Any) -> None:
        filepath = str(tmp_path / "deep" / "nested" / "dir" / "data.json")
        JsonStorage.save(filepath, {"auto": True})
        assert os.path.exists(filepath)
        result = JsonStorage.load(filepath)
        assert result == {"auto": True}
