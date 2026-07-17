import json
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class GameDatabase:
    """Manages local game database with atomic writes."""

    def __init__(self, db_path: str = "data/games.json"):
        self.db_path = db_path
        self.games: Dict[int, Dict[str, Any]] = {}
        self._ensure_directory()
        self._load_database()

    def _ensure_directory(self):
        """Ensure database directory exists."""
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)

    def _load_database(self):
        """Load existing database if it exists."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Support both array and object formats
                    if isinstance(data, list):
                        self.games = {game["id"]: game for game in data}
                    else:
                        self.games = {int(k): v for k, v in data.items()}
                logger.info(f"Loaded {len(self.games)} games from database")
            except Exception as e:
                logger.error(f"Failed to load database: {e}")
                self.games = {}
        else:
            self.games = {}
            logger.info("Starting with empty database")

    def _save_database(self):
        """
        Save database to disk atomically.
        Writes to temporary file first, then moves to final location.
        """
        temp_path = self.db_path + ".tmp"
        try:
            # Convert to format: keyed by ID
            db_dict = self.games.copy()

            # Write to temporary file
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(db_dict, f, indent=2, ensure_ascii=False)

            # Move temp file to actual location (atomic on most systems)
            os.replace(temp_path, self.db_path)
            logger.debug(f"Saved database with {len(self.games)} games")

        except Exception as e:
            logger.error(f"Failed to save database: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def add_or_update_game(self, game_id: int, game_data: Dict[str, Any]) -> bool:
        """
        Add or update a game in the database.
        Immediately persists to disk.
        Returns True if successful.
        """
        try:
            # Ensure ID is in game data
            game_data["id"] = game_id

            # Add/update timestamp
            if "updated_at" not in game_data:
                game_data["updated_at"] = datetime.utcnow().isoformat()
            else:
                game_data["updated_at"] = datetime.utcnow().isoformat()

            self.games[game_id] = game_data

            # Immediately save
            self._save_database()

            logger.info(f"Game {game_id} saved to database")
            return True

        except Exception as e:
            logger.error(f"Failed to add/update game {game_id}: {e}")
            return False

    def get_game(self, game_id: int) -> Optional[Dict[str, Any]]:
        """Get a game by ID."""
        return self.games.get(game_id)

    def get_all_games(self) -> Dict[int, Dict[str, Any]]:
        """Get all games."""
        return self.games.copy()

    def get_game_count(self) -> int:
        """Get total number of games."""
        return len(self.games)

    def game_exists(self, game_id: int) -> bool:
        """Check if a game exists."""
        return game_id in self.games

    def validate_json(self) -> bool:
        """Validate that database file is valid JSON."""
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                json.load(f)
            return True
        except Exception as e:
            logger.error(f"Invalid JSON in database: {e}")
            return False
