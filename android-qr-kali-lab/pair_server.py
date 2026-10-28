"""Serve the pairing page and record pairing requests.

This is a lab demo: it serves index.html and answers POST /pair, nothing more.
Optional --token adds a shared secret so random LAN devices cannot pair.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import settings

INDEX_PATH = Path(__file__).with_name("index.html")
MAX_BODY = 64 * 1024


class Handler(BaseHTTPRequestHandler):
    server_version = "KaliPairLab/1.0"

    token = ""
    quiet = False

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: dict) -> None:
        self._send(status, json.dumps(payload).encode(), "application/json")

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        path = urlparse(self.path).path

        if path in ("/", "/index.html"):
            try:
                html = INDEX_PATH.read_bytes()
            except FileNotFoundError:
                self._send_json(404, {"error": "index.html not found"})
                return
            self._send(200, html, "text/html; charset=utf-8")
        elif path == "/health":
            self._send_json(200, {"status": "ok"})
        elif path == "/favicon.ico":
            self._send(204, b"", "image/x-icon")
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if urlparse(self.path).path != "/pair":
            self._send_json(404, {"error": "not found"})
            return

        if self.token and self.headers.get("X-Pair-Token", "") != self.token:
            print(f"[!] Rejected pairing attempt from {self.client_address[0]} (bad token)")
            self._send_json(401, {"status": "unauthorized"})
            return

        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(min(length, MAX_BODY))

        stamp = time.strftime("%H:%M:%S")
        print(f"[+] {stamp} pairing request from {self.client_address[0]}")
        self._send_json(200, {"status": "paired"})

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        if not self.quiet:
            super().log_message(format, *args)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the Kali pairing page.")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument(
        "--port",
        type=int,
        default=settings.pair_port(),
        help=f"Port to listen on (default: {settings.pair_port()})",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("PAIR_TOKEN", ""),
        help="Require this token via the X-Pair-Token header (default: $PAIR_TOKEN)",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress request logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    Handler.token = args.token
    Handler.quiet = args.quiet

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{settings.lan_ip() if args.host == '0.0.0.0' else args.host}:{args.port}"

    print(f"Pairing server listening on {args.host}:{args.port}")
    print(f"Open {url}/ on the phone, or scan the QR code in mirror_app.py")
    if args.token:
        print(f"Token required: open {url}/?token={args.token}")
    print("Ctrl+C to stop.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
