"""
Progress Manager module.

Manages named progress files for a user's wanted parts pickup sessions.
Each progress file is stored as a JSON file in user_data/{username}/progress/.
"""

import ast
import json
import logging
import re
import tempfile
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ProgressManager:
    """Manages named progress files for a user."""

    # Characters invalid for filenames on Windows and Linux
    _INVALID_CHARS_PATTERN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

    def __init__(self, user_progress_dir: Path):
        """
        Args:
            user_progress_dir: Path to user_data/{username}/progress/
        """
        self.user_progress_dir = user_progress_dir
        self.user_progress_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """
        Remove characters invalid for filenames on Windows and Linux.
        Strips: < > : " / \\ | ? * and control characters (0x00-0x1F).
        Trims whitespace and trailing dots.

        Returns:
            Sanitized string safe for use as a filename stem.
        """
        sanitized = ProgressManager._INVALID_CHARS_PATTERN.sub("", name)
        sanitized = sanitized.strip()
        sanitized = sanitized.rstrip(".")
        return sanitized

    @staticmethod
    def generate_default_name() -> str:
        """Generate a default name based on current datetime: YYYY-MM-DD_HH-MM-SS."""
        return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def list_progress_files(self) -> list[dict]:
        """
        List all progress files with metadata only (no found_counts loaded).

        Returns:
            List of dicts with keys: 'filename', 'name', 'last_updated', 'wanted_csv_files'
            Sorted by last_updated descending (most recent first).
        """
        result = []
        for file_path in self.user_progress_dir.glob("*.json"):
            try:
                raw = file_path.read_text(encoding="utf-8")
                data = json.loads(raw)
                result.append({
                    "filename": file_path.name,
                    "name": file_path.stem,
                    "last_updated": data.get("last_updated", ""),
                    "wanted_csv_files": data.get("wanted_csv_files", []),
                })
            except json.JSONDecodeError:
                logger.warning("Skipping corrupted progress file: %s", file_path.name)
                continue

        result.sort(key=lambda x: x["last_updated"], reverse=True)
        return result

    def find_matching_progress(self, wanted_csv_files: list[str]) -> list[dict]:
        """
        Find progress files whose wanted_csv_files match the given list.

        Args:
            wanted_csv_files: List of current wanted CSV file names (will be sorted for comparison).

        Returns:
            List of matching metadata dicts (same format as list_progress_files).
        """
        sorted_wanted = sorted(wanted_csv_files)
        return [
            entry for entry in self.list_progress_files()
            if entry["wanted_csv_files"] == sorted_wanted
        ]


    def save_progress(self, name: str, found_counts: dict, set_found_counts: dict,
                      wanted_csv_files: list[str],
                      merged_df_csv: str | None = None,
                      locations_index: dict | None = None) -> Path:
        """
        Save progress to a named JSON file using atomic write.

        Args:
            name: Display name for the progress file (used as filename stem after sanitization).
            found_counts: Dict mapping (part, color, location) tuples to found count.
            set_found_counts: Dict mapping (part, color, set_key) tuples to found count.
            wanted_csv_files: Sorted list of wanted CSV file names.
            merged_df_csv: Optional CSV string of the merged DataFrame for full session restore.
            locations_index: Optional dict mapping locations to image path lists.

        Returns:
            Path to the saved file.

        Raises:
            ValueError: If sanitized name is empty.
        """
        sanitized = self.sanitize_filename(name)
        if not sanitized:
            raise ValueError("Progress name is empty after sanitization.")

        target_path = self.user_progress_dir / f"{sanitized}.json"

        data = {
            "found_counts": {str(k): v for k, v in found_counts.items()},
            "set_found_counts": {str(k): v for k, v in set_found_counts.items()},
            "wanted_csv_files": sorted(wanted_csv_files),
            "last_updated": datetime.now().isoformat(),
        }
        if merged_df_csv is not None:
            data["merged_df_csv"] = merged_df_csv
        if locations_index is not None:
            data["locations_index"] = {str(k): [str(p) for p in v] for k, v in locations_index.items()}

        tmp_fd = None
        tmp_path = None
        try:
            tmp_fd = tempfile.NamedTemporaryFile(
                mode="w", suffix=".tmp", dir=self.user_progress_dir, delete=False
            )
            tmp_path = tmp_fd.name
            json.dump(data, tmp_fd, indent=2)
            tmp_fd.close()
            tmp_fd = None
            Path(tmp_path).replace(target_path)
            saved_path = target_path
            tmp_path = None  # rename succeeded, no cleanup needed
            return saved_path
        finally:
            if tmp_fd is not None:
                tmp_fd.close()
            if tmp_path is not None:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except OSError:
                    pass

    def load_progress(self, filename: str) -> dict:
        """
        Load full progress data from a file.

        Args:
            filename: The JSON filename to load.

        Returns:
            Dict with keys: 'found_counts', 'set_found_counts', 'wanted_csv_files', 'last_updated'
            found_counts and set_found_counts keys are restored to tuples via ast.literal_eval().

        Raises:
            FileNotFoundError: If file does not exist.
            json.JSONDecodeError: If file contains invalid JSON.
        """
        file_path = self.user_progress_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Progress file not found: {filename}")

        raw = file_path.read_text(encoding="utf-8")
        data = json.loads(raw)

        found_counts = {
            ast.literal_eval(k): v for k, v in data.get("found_counts", {}).items()
        }
        set_found_counts = {
            ast.literal_eval(k): v for k, v in data.get("set_found_counts", {}).items()
        }

        result = {
            "found_counts": found_counts,
            "set_found_counts": set_found_counts,
            "wanted_csv_files": data.get("wanted_csv_files", []),
            "last_updated": data.get("last_updated"),
        }
        if "merged_df_csv" in data:
            result["merged_df_csv"] = data["merged_df_csv"]
        if "locations_index" in data:
            result["locations_index"] = data["locations_index"]
        return result

    def rename_progress(self, old_filename: str, new_name: str) -> str:
        """
        Rename a progress file.

        Args:
            old_filename: Current filename.
            new_name: New display name (will be sanitized).

        Returns:
            New filename after sanitization.

        Raises:
            FileExistsError: If new name conflicts with existing file.
            ValueError: If sanitized name is empty.
        """
        sanitized = self.sanitize_filename(new_name)
        if not sanitized:
            raise ValueError("Progress name is empty after sanitization.")

        new_filename = f"{sanitized}.json"
        old_path = self.user_progress_dir / old_filename
        new_path = self.user_progress_dir / new_filename

        if new_path.exists() and old_path != new_path:
            raise FileExistsError(f"A progress file named '{sanitized}' already exists.")

        old_path.rename(new_path)
        return new_filename

    def delete_progress(self, filename: str) -> None:
        """
        Delete a progress file. Silently succeeds if the file is already gone.

        Args:
            filename: The JSON filename to delete.
        """
        file_path = self.user_progress_dir / filename
        file_path.unlink(missing_ok=True)

