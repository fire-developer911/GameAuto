import json
import logging
import os
from typing import Dict, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ResumeManager:
    """Manages scraping progress for resuming interrupted runs."""

    def __init__(self, progress_file: str = "data/progress.json", failed_file: str = "data/failed.json"):
        self.progress_file = progress_file
        self.failed_file = failed_file
        self._ensure_directory()
        self.progress = self._load_progress()
        self.failed_ids = self._load_failed()

    def _ensure_directory(self):
        """Ensure data directory exists."""
        os.makedirs(os.path.dirname(self.progress_file) or ".", exist_ok=True)

    def _load_progress(self) -> Dict[str, Any]:
        """Load progress from file or return defaults."""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load progress: {e}")
                return {"last_completed": 0, "updated": None}
        return {"last_completed": 0, "updated": None}

    def _load_failed(self) -> set:
        """Load list of failed IDs."""
        if os.path.exists(self.failed_file):
            try:
                with open(self.failed_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return set(data.get("failed_ids", []))
            except Exception as e:
                logger.error(f"Failed to load failed list: {e}")
                return set()
        return set()

    def _save_progress(self):
        """Save progress to file."""
        try:
            self.progress["updated"] = datetime.utcnow().isoformat()
            os.makedirs(os.path.dirname(self.progress_file) or ".", exist_ok=True)

            temp_path = self.progress_file + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.progress, f, indent=2)
            os.replace(temp_path, self.progress_file)

            logger.debug(f"Progress saved: {self.progress}")
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")

    def _save_failed(self):
        """Save failed IDs to file."""
        try:
            os.makedirs(os.path.dirname(self.failed_file) or ".", exist_ok=True)

            temp_path = self.failed_file + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"failed_ids": sorted(list(self.failed_ids)), "updated": datetime.utcnow().isoformat()},
                    f,
                    indent=2,
                )
            os.replace(temp_path, self.failed_file)

            logger.debug(f"Failed list saved: {len(self.failed_ids)} games")
        except Exception as e:
            logger.error(f"Failed to save failed list: {e}")

    def mark_completed(self, game_id: int):
        """Mark a game as completed."""
        self.progress["last_completed"] = game_id
        self._save_progress()

    def mark_failed(self, game_id: int):
        """Mark a game as failed."""
        self.failed_ids.add(game_id)
        self._save_failed()

    def get_next_id(self, first_id: int, last_id: int) -> int:
        """Get the next ID to scrape."""
        last_completed = self.progress.get("last_completed", 0)

        if last_completed >= last_id:
            logger.info("All IDs have been scraped")
            return last_id + 1

        next_id = last_completed + 1
        if next_id < first_id:
            next_id = first_id

        return next_id

    def reset_progress(self):
        """Reset progress to start from beginning."""
        self.progress = {"last_completed": 0, "updated": None}
        self._save_progress()
        logger.info("Progress reset")

    def get_stats(self) -> Dict[str, Any]:
        """Get scraping statistics."""
        return {
            "last_completed": self.progress.get("last_completed", 0),
            "failed_count": len(self.failed_ids),
            "failed_ids": sorted(list(self.failed_ids)),
            "last_updated": self.progress.get("updated"),
        }
