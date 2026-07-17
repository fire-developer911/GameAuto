import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import time

from telegram_client import TelegramClientWrapper
from parser import GameMetadataParser
from database import GameDatabase
from downloader import FileDownloader
from resume import ResumeManager

logger = logging.getLogger(__name__)


class PS4Scraper:
    """Main scraper for PS4 games from Telegram bot."""

    def __init__(
        self,
        api_id: int,
        api_hash: str,
        phone: str,
        bot_username: str,
        activation_password: str,
        first_id: int,
        last_id: int,
        retry_attempts: int = 3,
        retry_delay_base: int = 2,
        message_wait_timeout: int = 30,
    ):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.bot_username = bot_username
        self.activation_password = activation_password
        self.first_id = first_id
        self.last_id = last_id
        self.retry_attempts = retry_attempts
        self.retry_delay_base = retry_delay_base
        self.message_wait_timeout = message_wait_timeout

        self.telegram_client = TelegramClientWrapper(api_id, api_hash, phone)
        self.database = GameDatabase()
        self.downloader = FileDownloader()
        self.resume_manager = ResumeManager()

        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "start_time": None,
        }

    async def initialize(self) -> bool:
        """Initialize: connect, login, find bot, send activation."""
        try:
            # Connect and login
            if not await self.telegram_client.connect_and_login():
                return False

            # Get bot entity
            if not await self.telegram_client.get_bot_entity(self.bot_username):
                return False

            # Send activation password
            logger.info(f"Sending activation password: {self.activation_password}")
            if not await self.telegram_client.send_message(self.activation_password):
                return False

            # Wait for activation response and discard it
            messages = await self.telegram_client.wait_for_messages(timeout=self.message_wait_timeout)
            logger.info(f"Activation sent, bot responded with {len(messages)} message(s)")

            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False

    async def _send_command_with_retry(self, command: str) -> bool:
        """Send a command with exponential backoff retry."""
        for attempt in range(self.retry_attempts):
            try:
                if await self.telegram_client.send_message(command):
                    return True
            except Exception as e:
                logger.error(f"Command '{command}' attempt {attempt + 1} failed: {e}")

            if attempt < self.retry_attempts - 1:
                delay = self.retry_delay_base ** (attempt + 1)
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)

        return False

    async def scrape_download(self, game_id: int) -> Optional[Dict[str, Any]]:
        """Scrape /download<ID> response."""
        command = f"/download{game_id}"
        logger.info(f"Scraping {command}")

        # Send command
        if not await self._send_command_with_retry(command):
            logger.error(f"Game {game_id}: Failed to send download command")
            return None

        # Wait for response
        try:
            messages = await self.telegram_client.wait_for_messages(timeout=self.message_wait_timeout)
        except Exception as e:
            logger.error(f"Game {game_id}: Failed waiting for response: {e}")
            return None

        if not messages:
            logger.warning(f"Game {game_id}: No response from bot")
            return None

        # Parse response
        torrent_data = GameMetadataParser.parse_torrent_response(messages)

        if not torrent_data:
            logger.warning(f"Game {game_id}: Could not parse torrent data")
            return None

        # Download torrent file
        try:
            # Find message with document
            for msg in messages:
                if msg.get("raw") and msg["raw"].document:
                    torrent_path = await self.downloader.download_torrent(
                        self.telegram_client, msg["raw"], game_id
                    )
                    if torrent_path:
                        torrent_data["local_path"] = torrent_path
                    break
        except Exception as e:
            logger.error(f"Game {game_id}: Failed to download torrent: {e}")

        return torrent_data

    async def scrape_cover(self, game_id: int) -> Optional[Dict[str, Any]]:
        """Scrape /cover<ID> response."""
        command = f"/cover{game_id}"
        logger.info(f"Scraping {command}")

        # Send command
        if not await self._send_command_with_retry(command):
            logger.error(f"Game {game_id}: Failed to send cover command")
            return None

        # Wait for response
        try:
            messages = await self.telegram_client.wait_for_messages(timeout=self.message_wait_timeout)
        except Exception as e:
            logger.error(f"Game {game_id}: Failed waiting for response: {e}")
            return None

        if not messages:
            logger.warning(f"Game {game_id}: No response from bot")
            return None

        # Parse response
        cover_data = GameMetadataParser.parse_cover_response(messages)

        if not cover_data:
            logger.warning(f"Game {game_id}: Could not parse cover data")
            return None

        # Download cover image
        try:
            for msg in messages:
                if msg.get("raw") and msg["raw"].photo:
                    cover_path = await self.downloader.download_cover(
                        self.telegram_client, msg["raw"], game_id
                    )
                    if cover_path:
                        cover_data["local_path"] = cover_path
                    break
        except Exception as e:
            logger.error(f"Game {game_id}: Failed to download cover: {e}")

        return cover_data

    async def scrape_game(self, game_id: int) -> bool:
        """Scrape a single game (download + cover)."""
        try:
            # Scrape download
            download_data = await self.scrape_download(game_id)
            if not download_data:
                logger.error(f"Game {game_id}: Download scrape failed")
                return False

            # Small delay between commands
            await asyncio.sleep(1)

            # Scrape cover
            cover_data = await self.scrape_cover(game_id)
            if not cover_data:
                logger.error(f"Game {game_id}: Cover scrape failed")
                return False

            # Wait before next game
            await asyncio.sleep(2)

            # Build game object
            game_obj = {
                "id": game_id,
                "title": cover_data["metadata"].get("title", "Unknown"),
                "torrent": {
                    "filename": download_data.get("torrent_filename"),
                    "size": download_data.get("torrent_size"),
                    "telegram_file_id": download_data.get("telegram_file_id"),
                    "local_path": download_data.get("local_path"),
                },
                "cover": {
                    "telegram_file_id": cover_data.get("cover_file_id"),
                    "local_path": cover_data.get("local_path"),
                },
                "metadata": cover_data["metadata"],
                "raw_cover_text": cover_data.get("text", ""),
                "scraped_at": datetime.utcnow().isoformat(),
            }

            # Save to database
            if self.database.add_or_update_game(game_id, game_obj):
                self.resume_manager.mark_completed(game_id)
                self.stats["successful"] += 1
                logger.info(f"Game {game_id}: Successfully scraped and saved")
                return True
            else:
                logger.error(f"Game {game_id}: Failed to save to database")
                return False

        except Exception as e:
            logger.error(f"Game {game_id}: Scrape error: {e}")
            return False

    async def run(self, resume: bool = True):
        """Run the scraper."""
        logger.info("=" * 60)
        logger.info("PS4 GAMES TELEGRAM SCRAPER")
        logger.info("=" * 60)

        # Initialize
        if not await self.initialize():
            logger.error("Failed to initialize scraper")
            await self.telegram_client.disconnect()
            return

        # Get starting point
        if resume:
            start_id = self.resume_manager.get_next_id(self.first_id, self.last_id)
            logger.info(f"Resuming from ID {start_id}")
        else:
            start_id = self.first_id
            self.resume_manager.reset_progress()
            logger.info(f"Starting fresh from ID {start_id}")

        self.stats["start_time"] = datetime.now()
        total_games = self.last_id - start_id + 1

        logger.info(f"Scraping {total_games} games (IDs {start_id}-{self.last_id})")

        # Main loop
        for game_id in range(start_id, self.last_id + 1):
            self.stats["total_processed"] += 1

            progress_pct = (self.stats["total_processed"] / total_games) * 100
            elapsed = datetime.now() - self.stats["start_time"]

            logger.info(
                f"\n[{self.stats['total_processed']}/{total_games}] ({progress_pct:.1f}%) "
                f"Processing game {game_id} | Elapsed: {elapsed}"
            )

            if await self.scrape_game(game_id):
                pass  # Success logged in scrape_game
            else:
                self.stats["failed"] += 1
                self.resume_manager.mark_failed(game_id)
                logger.warning(f"Game {game_id}: Added to failed list")

        # Final report
        await self.finalize()

    async def finalize(self):
        """Clean up and print final report."""
        try:
            await self.telegram_client.disconnect()
        except Exception as e:
            logger.error(f"Disconnect error: {e}")

        total_time = datetime.now() - self.stats["start_time"]
        logger.info("\n" + "=" * 60)
        logger.info("SCRAPING COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total processed: {self.stats['total_processed']}")
        logger.info(f"Successful: {self.stats['successful']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Total time: {total_time}")
        logger.info(f"Database size: {self.database.get_game_count()} games")

        stats = self.resume_manager.get_stats()
        logger.info(f"Failed IDs: {stats['failed_ids']}")
