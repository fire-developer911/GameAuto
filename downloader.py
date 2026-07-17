import os
import logging
from typing import Optional
from datetime import datetime
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto

logger = logging.getLogger(__name__)


class FileDownloader:
    """Handles downloading files from Telegram to local storage."""

    def __init__(self, torrents_dir: str = "data/torrents", covers_dir: str = "data/covers"):
        self.torrents_dir = torrents_dir
        self.covers_dir = covers_dir
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure all required directories exist."""
        os.makedirs(self.torrents_dir, exist_ok=True)
        os.makedirs(self.covers_dir, exist_ok=True)

    async def download_torrent(self, telegram_client, message, game_id: int) -> Optional[str]:
        """
        Download torrent file from Telegram.
        telegram_client is TelegramClientWrapper, message is raw Telethon Message object.
        Returns local file path if successful.
        """
        try:
            # Verify message has document
            if not message or not hasattr(message, 'media') or not message.media:
                logger.warning(f"Game {game_id}: No media in message")
                return None

            if not isinstance(message.media, MessageMediaDocument):
                logger.warning(f"Game {game_id}: Media is not a document")
                return None

            file_path = os.path.join(self.torrents_dir, f"{game_id}.torrent")

            # Check if already downloaded
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                if size > 0:
                    logger.debug(f"Game {game_id}: Torrent already downloaded ({size} bytes)")
                    return file_path

            # Download the file
            logger.debug(f"Game {game_id}: Starting torrent download")
            await telegram_client.client.download_media(message.media, file_path)

            # Verify download
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                file_size = os.path.getsize(file_path)
                logger.info(f"Game {game_id}: Torrent downloaded ({file_size} bytes)")
                return file_path
            else:
                logger.error(f"Game {game_id}: Downloaded torrent is empty or doesn't exist")
                if os.path.exists(file_path):
                    os.remove(file_path)
                return None

        except Exception as e:
            logger.error(f"Game {game_id}: Failed to download torrent: {type(e).__name__}: {e}")
            return None

    async def download_cover(self, telegram_client, message, game_id: int) -> Optional[str]:
        """
        Download cover image from Telegram.
        telegram_client is TelegramClientWrapper, message is raw Telethon Message object.
        Returns local file path if successful.
        """
        try:
            # Verify message has photo
            if not message or not hasattr(message, 'media') or not message.media:
                logger.warning(f"Game {game_id}: No media in message")
                return None

            if not isinstance(message.media, MessageMediaPhoto):
                logger.warning(f"Game {game_id}: Media is not a photo")
                return None

            file_path = os.path.join(self.covers_dir, f"{game_id}.jpg")

            # Check if already downloaded
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                if size > 0:
                    logger.debug(f"Game {game_id}: Cover already downloaded ({size} bytes)")
                    return file_path

            # Download the file
            logger.debug(f"Game {game_id}: Starting cover download")
            await telegram_client.client.download_media(message.media, file_path)

            # Verify download
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                file_size = os.path.getsize(file_path)
                logger.info(f"Game {game_id}: Cover downloaded ({file_size} bytes)")
                return file_path
            else:
                logger.error(f"Game {game_id}: Downloaded cover is empty or doesn't exist")
                if os.path.exists(file_path):
                    os.remove(file_path)
                return None

        except Exception as e:
            logger.error(f"Game {game_id}: Failed to download cover: {type(e).__name__}: {e}")
            return None

    def get_torrent_path(self, game_id: int) -> str:
        """Get the path where a torrent should be stored."""
        return os.path.join(self.torrents_dir, f"{game_id}.torrent")

    def get_cover_path(self, game_id: int) -> str:
        """Get the path where a cover should be stored."""
        return os.path.join(self.covers_dir, f"{game_id}.jpg")

    def torrent_exists(self, game_id: int) -> bool:
        """Check if torrent file exists."""
        return os.path.exists(self.get_torrent_path(game_id))

    def cover_exists(self, game_id: int) -> bool:
        """Check if cover file exists."""
        return os.path.exists(self.get_cover_path(game_id))
