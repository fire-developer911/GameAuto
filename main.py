#!/usr/bin/env python3
"""
PS4 Games Telegram Scraper
Scrapes PS4 game metadata from Telegram bot using official API.
"""

import asyncio
import json
import logging
import sys
import argparse
from pathlib import Path

from scraper import PS4Scraper
from server import SearchServer


def setup_logging():
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/scraper.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    # Reduce noise from telethon
    logging.getLogger("telethon").setLevel(logging.WARNING)


def load_config(config_file: str = "config.json") -> dict:
    """Load configuration from file."""
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {config_file} not found")
        print("Please create config.json with your Telegram API credentials")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: {config_file} is not valid JSON")
        sys.exit(1)


async def scrape_games(config: dict, resume: bool = True):
    """Run the scraper."""
    scraper = PS4Scraper(
        api_id=config["telegram"]["api_id"],
        api_hash=config["telegram"]["api_hash"],
        phone=config["telegram"]["phone"],
        bot_username=config["bot"]["username"],
        activation_password=config["bot"]["activation_password"],
        first_id=config["scraping"]["first_id"],
        last_id=config["scraping"]["last_id"],
        retry_attempts=config["scraping"]["retry_attempts"],
        retry_delay_base=config["scraping"]["retry_delay_base"],
        message_wait_timeout=config["scraping"]["message_wait_timeout"],
    )

    await scraper.run(resume=resume)


async def run_server(config: dict):
    """Run the search server."""
    db_path = Path(config["folders"]["data_dir"]) / "games.json"
    await SearchServer.run_server(
        host=config["server"]["host"],
        port=config["server"]["port"],
        db_path=str(db_path),
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="PS4 Games Telegram Scraper")
    parser.add_argument(
        "command",
        choices=["scrape", "server"],
        help="Command to run: 'scrape' to scrape games, 'server' to run search server",
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to config file (default: config.json)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Start from beginning (don't resume)",
    )

    args = parser.parse_args()

    # Setup logging
    Path("logs").mkdir(exist_ok=True)
    setup_logging()

    logger = logging.getLogger(__name__)

    # Load configuration
    config = load_config(args.config)

    # Ensure data directories exist
    for dir_key in ["torrents_dir", "covers_dir", "logs_dir"]:
        Path(config["folders"][dir_key]).mkdir(parents=True, exist_ok=True)

    # Run command
    try:
        if args.command == "scrape":
            # Validate config
            if not config["telegram"]["api_id"] or not config["telegram"]["api_hash"]:
                print("Error: API ID and API Hash must be configured")
                sys.exit(1)

            if not config["telegram"]["phone"]:
                print("Error: Phone number must be configured")
                sys.exit(1)

            asyncio.run(scrape_games(config, resume=not args.no_resume))

        elif args.command == "server":
            logger.info("Starting search server")
            asyncio.run(run_server(config))

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
