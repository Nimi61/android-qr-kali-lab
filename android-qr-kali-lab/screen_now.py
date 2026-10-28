"""Generate a QR code PNG for arbitrary text or a URL."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import qrcode


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a QR code image.")
    parser.add_argument("data", help="Text or URL to encode")
    parser.add_argument(
        "-o",
        "--output",
        default="qr.png",
        help="Output PNG path (default: qr.png)",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Open the image with the default viewer after writing it",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    path = Path(args.output).expanduser()

    image = qrcode.make(args.data)
    image.save(path)
    print(f"Wrote {path} ({path.stat().st_size} bytes)")

    if args.show:
        image.show()
    return 0


if __name__ == "__main__":
    sys.exit(main())
