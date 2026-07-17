import os
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramClientWrapper:
    """Wrapper around Telethon TelegramClient for PS4 bot interaction."""

    def __init__(self, api_id: int, api_hash: str, phone: str, session_dir: str = "sessions"):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.session_dir = session_dir
        self.session_file = os.path.join(session_dir, f"session_{phone.replace('+', '')}")

        # Create session directory if needed
        os.makedirs(session_dir, exist_ok=True)

        self.client = TelegramClient(self.session_file, api_id, api_hash)
        self.bot_entity = None
        self.last_messages: List[Dict[str, Any]] = []
        self.message_event = asyncio.Event()

    async def connect_and_login(self) -> bool:
        """
        Connect to Telegram and login if needed.
        Returns True if successful.
        """
        try:
            await self.client.connect()

            # Check if already logged in
            if not await self.client.is_user_authorized():
                logger.info(f"Requesting login code for {self.phone}")
                await self.client.send_code_request(self.phone)

                # Get login code from input
                code = input("Enter login code: ")
                try:
                    await self.client.sign_in(self.phone, code)
                except Exception as e:
                    logger.error(f"Login failed: {e}")
                    return False

            logger.info("Successfully authenticated with Telegram")
            return True

        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False

    async def get_bot_entity(self, bot_username: str):
        """Get the bot entity by username."""
        try:
            self.bot_entity = await self.client.get_entity(bot_username)
            logger.info(f"Found bot: {bot_username}")
            return self.bot_entity
        except Exception as e:
            logger.error(f"Failed to find bot {bot_username}: {e}")
            return None

    async def send_message(self, message: str) -> bool:
        """
        Send a message to the bot.
        Returns True if successful.
        """
        if not self.bot_entity:
            logger.error("Bot entity not set. Call get_bot_entity first.")
            return False

        try:
            await self.client.send_message(self.bot_entity, message)
            logger.debug(f"Sent message: {message}")
            return True
        except FloodWaitError as e:
            logger.warning(f"FloodWait: sleeping for {e.seconds} seconds")
            await asyncio.sleep(e.seconds)
            # Retry once after flood wait
            try:
                await self.client.send_message(self.bot_entity, message)
                return True
            except Exception as retry_error:
                logger.error(f"Failed to send message after FloodWait: {retry_error}")
                return False
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    async def wait_for_messages(self, timeout: int = 30) -> List[Dict[str, Any]]:
        """
        Wait for bot response messages.
        Collects all messages until a timeout occurs.
        """
        self.last_messages = []
        start_time = datetime.now()

        @self.client.on(events.NewMessage(chats=self.bot_entity))
        async def handle_message(event):
            msg_data = {
                "id": event.message.id,
                "text": event.message.text or "",
                "document": event.message.document,
                "photo": event.message.photo,
                "media": event.message.media,
                "raw": event.message,
            }
            self.last_messages.append(msg_data)
            logger.debug(f"Received message: {msg_data['id']}")

        try:
            # Wait for at least one message
            while len(self.last_messages) == 0:
                await asyncio.sleep(0.1)
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > timeout:
                    logger.warning(f"Timeout waiting for initial message after {timeout}s")
                    break

            # Wait for more messages with timeout
            quiet_time = 0
            while True:
                last_count = len(self.last_messages)
                await asyncio.sleep(0.5)
                elapsed = (datetime.now() - start_time).total_seconds()

                if len(self.last_messages) == last_count:
                    quiet_time += 0.5
                else:
                    quiet_time = 0

                # If no new messages for 2 seconds or overall timeout, stop
                if quiet_time >= 2.0 or elapsed > timeout:
                    break

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error waiting for messages: {e}")
        finally:
            self.client.remove_event_handler(handle_message)

        logger.info(f"Collected {len(self.last_messages)} messages")
        return self.last_messages

    async def download_file(self, media, file_path: str) -> bool:
        """
        Download a file from Telegram media.
        Returns True if successful.
        """
        try:
            await self.client.download_media(media, file_path)
            logger.info(f"Downloaded file to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            return False

    async def disconnect(self):
        """Disconnect from Telegram."""
        await self.client.disconnect()
        logger.info("Disconnected from Telegram")
