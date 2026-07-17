import asyncio
import logging
from aiohttp import web
import json
from pathlib import Path
from typing import Dict, Any, List

from database import GameDatabase

logger = logging.getLogger(__name__)


class SearchServer:
    """Local HTTP server for searching games database."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8080, db_path: str = "data/games.json"):
        self.host = host
        self.port = port
        self.database = GameDatabase(db_path)
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_get("/", self.handle_root)
        self.app.router.add_get("/games", self.handle_all_games)
        self.app.router.add_get("/games/{game_id}", self.handle_game_by_id)
        self.app.router.add_get("/search", self.handle_search)
        self.app.router.add_static("/covers/", path="data/covers", name="covers")
        self.app.router.add_static("/torrents/", path="data/torrents", name="torrents")

    async def handle_root(self, request: web.Request) -> web.Response:
        """Handle root endpoint with API documentation."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>PS4 Games API</title>
            <style>
                body { font-family: monospace; margin: 20px; }
                h1 { color: #333; }
                .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-left: 4px solid #0066cc; }
                code { background: #eee; padding: 2px 5px; }
            </style>
        </head>
        <body>
            <h1>PS4 Games Database API</h1>
            <h2>Endpoints:</h2>
            <div class="endpoint">
                <strong>GET /games</strong><br>
                Returns all games in database
            </div>
            <div class="endpoint">
                <strong>GET /games/{id}</strong><br>
                Returns specific game by ID<br>
                Example: <code>/games/1</code>
            </div>
            <div class="endpoint">
                <strong>GET /search?q=query</strong><br>
                Search games by title (case-insensitive, partial match)<br>
                Example: <code>/search?q=Dark</code>
            </div>
            <div class="endpoint">
                <strong>GET /covers/{id}.jpg</strong><br>
                Download cover image<br>
                Example: <code>/covers/1.jpg</code>
            </div>
            <div class="endpoint">
                <strong>GET /torrents/{id}.torrent</strong><br>
                Download torrent file<br>
                Example: <code>/torrents/1.torrent</code>
            </div>
        </body>
        </html>
        """
        return web.Response(text=html, content_type="text/html")

    async def handle_all_games(self, request: web.Request) -> web.Response:
        """Return all games."""
        try:
            all_games = self.database.get_all_games()
            return web.json_response(all_games)
        except Exception as e:
            logger.error(f"Error retrieving games: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_game_by_id(self, request: web.Request) -> web.Response:
        """Return a specific game by ID."""
        try:
            game_id = int(request.match_info["game_id"])
            game = self.database.get_game(game_id)

            if not game:
                return web.json_response({"error": f"Game {game_id} not found"}, status=404)

            return web.json_response(game)
        except ValueError:
            return web.json_response({"error": "Invalid game ID"}, status=400)
        except Exception as e:
            logger.error(f"Error retrieving game: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_search(self, request: web.Request) -> web.Response:
        """Search games by title."""
        try:
            query = request.rel_url.query.get("q", "").strip()

            if not query:
                return web.json_response({"error": "Missing query parameter 'q'"}, status=400)

            query_lower = query.lower()
            all_games = self.database.get_all_games()

            # Search: case-insensitive, partial match on title
            results = {}
            for game_id, game in all_games.items():
                title = game.get("title", "").lower()
                if query_lower in title:
                    results[game_id] = game

            return web.json_response(
                {
                    "query": query,
                    "results": results,
                    "count": len(results),
                }
            )

        except Exception as e:
            logger.error(f"Search error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def start(self):
        """Start the server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        logger.info(f"Server started at http://{self.host}:{self.port}")
        return runner

    @staticmethod
    async def run_server(host: str = "127.0.0.1", port: int = 8080, db_path: str = "data/games.json"):
        """Run server indefinitely."""
        server = SearchServer(host, port, db_path)
        runner = await server.start()
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Shutting down server")
        finally:
            await runner.cleanup()
