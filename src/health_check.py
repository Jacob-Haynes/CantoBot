"""Health check HTTP server for monitoring bot status."""

import logging
import json
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP request handler for health check endpoint."""

    health_check_func: Callable[[], Awaitable[dict[str, bool | str]]] | None = None

    def log_message(self, format: str, *args: Any) -> None:
        """Override to use our logger instead of stderr."""
        logger.debug(f"{self.address_string()} - {format % args}")

    def do_GET(self) -> None:
        """Handle GET requests to /health endpoint."""
        if self.path == "/health":
            self.send_health_response()
        else:
            self.send_error(404, "Not Found")

    def send_health_response(self) -> None:
        """Send health check response."""
        try:
            if HealthCheckHandler.health_check_func:
                # Run async health check
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                health_data = loop.run_until_complete(HealthCheckHandler.health_check_func())
                loop.close()

                status_code = 200 if health_data.get("healthy", False) else 503
                response = json.dumps(health_data, indent=2)
            else:
                status_code = 200
                response = json.dumps({"status": "ok", "healthy": True}, indent=2)

            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response.encode())

        except Exception as e:
            logger.error(f"Health check error: {e}", exc_info=True)
            error_response = json.dumps({
                "status": "error",
                "healthy": False,
                "error": str(e)
            }, indent=2)
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(error_response)))
            self.end_headers()
            self.wfile.write(error_response.encode())


class HealthCheckServer:
    """HTTP server for health check endpoint."""

    def __init__(self, port: int = 8080, health_check_func: Callable[[], Awaitable[dict[str, bool | str]]] | None = None) -> None:
        self.port: int = port
        self.server: HTTPServer | None = None
        self.thread: Thread | None = None
        HealthCheckHandler.health_check_func = health_check_func

    def start(self) -> None:
        """Start the health check server in a separate thread."""
        try:
            self.server = HTTPServer(("0.0.0.0", self.port), HealthCheckHandler)
            self.thread = Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            logger.info(f"Health check server started on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to start health check server: {e}")

    def stop(self) -> None:
        """Stop the health check server."""
        if self.server:
            self.server.shutdown()
            logger.info("Health check server stopped")
