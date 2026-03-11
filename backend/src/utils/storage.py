"""JSON file-based persistence with atomic writes and backup support."""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import threading
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class JsonStorage:
    """Thread-safe JSON file storage with atomic writes and backup/restore.

    All writes are atomic: data is written to a temporary file first,
    then renamed to the target path to prevent corruption.
    """

    _lock = threading.Lock()

    @staticmethod
    def save(filepath: str, data: Any) -> None:
        """Write data as JSON atomically (temp file + rename).

        Args:
            filepath: Target file path.
            data: JSON-serializable data to write.
        """
        dirpath = os.path.dirname(filepath)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)

        with JsonStorage._lock:
            fd, tmp_path = tempfile.mkstemp(
                dir=dirpath or ".",
                suffix=".tmp",
            )
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(data, f, indent=2, default=str)
                # Atomic rename (on same filesystem)
                shutil.move(tmp_path, filepath)
                logger.debug("Saved %s", filepath)
            except Exception:
                # Clean up temp file on failure
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise

    @staticmethod
    def load(filepath: str) -> Any | None:
        """Read and parse a JSON file.

        Args:
            filepath: Path to the JSON file.

        Returns:
            Parsed data, or None if the file does not exist.
        """
        if not os.path.exists(filepath):
            return None

        with JsonStorage._lock:
            with open(filepath, "r") as f:
                data = json.load(f)
            logger.debug("Loaded %s", filepath)
            return data

    @staticmethod
    def backup(filepath: str, backup_dir: str = "data/backups") -> str | None:
        """Create a timestamped backup copy of a file.

        Args:
            filepath: Path to the file to back up.
            backup_dir: Directory to store backups (auto-created).

        Returns:
            Path to the backup file, or None if source doesn't exist.
        """
        if not os.path.exists(filepath):
            logger.warning("Cannot backup %s: file not found", filepath)
            return None

        os.makedirs(backup_dir, exist_ok=True)

        basename = os.path.basename(filepath)
        name, ext = os.path.splitext(basename)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_name = f"{name}_{timestamp}{ext}"
        backup_path = os.path.join(backup_dir, backup_name)

        with JsonStorage._lock:
            shutil.copy2(filepath, backup_path)
            logger.info("Backed up %s -> %s", filepath, backup_path)

        return backup_path

    @staticmethod
    def restore(backup_path: str, target_path: str) -> None:
        """Restore a file from a backup.

        Args:
            backup_path: Path to the backup file.
            target_path: Path to restore to.
        """
        dirpath = os.path.dirname(target_path)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)

        with JsonStorage._lock:
            shutil.copy2(backup_path, target_path)
            logger.info("Restored %s -> %s", backup_path, target_path)
