import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class GameMetadataParser:
    """
    Parse game metadata from Telegram bot responses.
    Flexible parser that matches field labels dynamically.
    """

    # Field mappings - key is the field name to extract, value is possible regex patterns
    FIELD_PATTERNS = {
        "title": [
            r"\[PS4\]\s+(.+?)\s+\[",  # Format: [PS4] Title [EUR/ENG]
            r"^\*\*(.+?)\*\*",  # Format: **Title**
            r"^(.+?)\s+\[",  # Format: Title [EUR/ENG]
        ],
        "region": [r"Region[:\s]+([A-Z]{3}|[A-Z,\s/]+)"],
        "year": [
            r"Year of issue[:\s]+(\d{2}\.\d{2}\.\d{4})",
            r"Released[:\s]+(\d{4})",
        ],
        "genre": [r"Genre[:\s]+(.+?)(?:\n|$)"],
        "developer": [r"Developer[:\s]+(.+?)(?:\n|$)"],
        "publisher": [r"Publish[a-z]+ house[:\s]+(.+?)(?:\n|$)"],
        "cusa": [r"CUSA[:\s]*([A-Z0-9]+)"],
        "version": [r"Game version[:\s]+([v\d.]+|\d+\.\d+)"],
        "firmware": [r"Minimum firmware[:\s]+(\d+\.\d+)"],
        "interface_languages": [r"Interface language[:\s]+(.+?)(?:\n|$)"],
        "voice_languages": [r"Voice language[:\s]+(.+?)(?:\n|$)"],
        "players": [r"(\d+)\s+player"],
        "rating": [r"Average rating[:\s]+([\d.]+)"],
        "ranking": [r"(\d+)\s+place in /toprated"],
        "release_type": [r"Type of releases[:\s]+(.+?)(?:\n|$)"],
        "tested": [r"Functionality tested[:\s]+(Yes|No)"],
    }

    @staticmethod
    def extract_field(text: str, field_name: str) -> Optional[str]:
        """
        Extract a field value from text using regex patterns.
        Returns None if not found.
        """
        if not text:
            return None

        patterns = GameMetadataParser.FIELD_PATTERNS.get(field_name, [])
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()

        return None

    @staticmethod
    def extract_all_fields(text: str) -> Dict[str, Any]:
        """
        Extract all known fields from text.
        Also captures any unknown field patterns.
        """
        extracted = {}

        # Extract known fields
        for field_name in GameMetadataParser.FIELD_PATTERNS.keys():
            value = GameMetadataParser.extract_field(text, field_name)
            if value:
                extracted[field_name] = value

        return extracted

    @staticmethod
    def parse_torrent_response(
        messages: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Parse /download<ID> response.
        Returns document info and metadata.
        """
        result = {
            "telegram_file_id": None,
            "torrent_filename": None,
            "torrent_size": None,
            "text": "",
        }

        for msg in messages:
            # Collect text
            if msg.get("text"):
                result["text"] += msg["text"] + "\n"

            # Extract document info
            if msg.get("document"):
                doc = msg["document"]
                result["telegram_file_id"] = doc.id
                result["torrent_filename"] = doc.attributes[0].file_name if doc.attributes else None
                result["torrent_size"] = doc.size

                logger.info(
                    f"Found torrent: {result['torrent_filename']} ({result['torrent_size']} bytes)"
                )

        return result if result["telegram_file_id"] else None

    @staticmethod
    def parse_cover_response(messages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Parse /cover<ID> response.
        Extracts cover image, description, and all metadata.
        """
        result = {
            "cover_file_id": None,
            "cover_filename": None,
            "screenshot_ids": [],
            "text": "",
            "metadata": {},
        }

        text_parts = []
        cover_found = False

        for msg in messages:
            # Extract photo (cover image or screenshots)
            if msg.get("photo") and not cover_found:
                photo = msg["photo"]
                result["cover_file_id"] = photo.id
                cover_found = True
                logger.info("Found cover image")

            elif msg.get("photo"):
                # Additional screenshots
                photo = msg["photo"]
                result["screenshot_ids"].append(photo.id)

            # Collect text for parsing
            if msg.get("text"):
                text_parts.append(msg["text"])

        full_text = "\n".join(text_parts)
        result["text"] = full_text

        # Parse metadata from full text
        result["metadata"] = GameMetadataParser.extract_all_fields(full_text)

        logger.info(f"Extracted metadata fields: {list(result['metadata'].keys())}")
        return result

    @staticmethod
    def clean_value(value: Any) -> Any:
        """Clean and normalize extracted values."""
        if not isinstance(value, str):
            return value

        # Remove trailing punctuation
        value = value.rstrip(".,;:")

        # Clean up multiple spaces
        value = re.sub(r"\s+", " ", value).strip()

        return value if value else None
