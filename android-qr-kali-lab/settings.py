"""Shared configuration for the Kali <-> Android lab scripts.

Kept dependency-free so every script (and the tests) can import it.
"""

from __future__ import annotations

import os
import socket

DEFAULT_PORT = 8765


def lan_ip() -> str:
    """Return this machine's best-guess LAN IP.

    Uses a UDP socket to a public address so the kernel picks the interface it
    would actually route through. No packets are sent. Falls back to loopback
    when there is no network.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def pair_port() -> int:
    """Port for the pairing page, overridable with PAIR_PORT."""
    raw = os.environ.get("PAIR_PORT", str(DEFAULT_PORT))
    try:
        port = int(raw)
    except ValueError as exc:
        raise ValueError(f"PAIR_PORT must be an integer, got {raw!r}") from exc
    if not 1 <= port <= 65535:
        raise ValueError(f"PAIR_PORT out of range: {port}")
    return port


def pair_url(host: str | None = None, port: int | None = None) -> str:
    """Build the URL the QR code points at."""
    return f"http://{host or lan_ip()}:{port or pair_port()}"
