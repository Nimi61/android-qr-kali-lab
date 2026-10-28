"""Mirror an Android screen on the desktop and tap on it to control the device.

The QR code points at the pairing page served by pair_server.py. Screen capture
and taps both go through adb, so the phone only needs USB debugging enabled.
"""

from __future__ import annotations

import argparse
import io
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import qrcode
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import adb_client
import geometry
import settings

FALLBACK_DEVICE_SIZE = (1080, 1920)


class QRDialog(QDialog):
    """Show the pairing URL as a QR code, generated in memory (no temp file)."""

    def __init__(self, url: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pair Android device")

        image_label = QLabel(self)
        image_label.setAlignment(Qt.AlignCenter)

        try:
            buffer = io.BytesIO()
            qrcode.make(url).save(buffer, format="PNG")
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.getvalue(), "PNG")
            image_label.setPixmap(pixmap)
        except Exception:  # a missing Pillow should not block the whole app
            image_label.setText("QR code unavailable.\nType the URL below on the phone.")

        caption = QLabel(url, self)
        caption.setAlignment(Qt.AlignCenter)
        caption.setTextInteractionFlags(Qt.TextSelectableByMouse)

        close_btn = QPushButton("Done / Connected", self)
        close_btn.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(image_label)
        layout.addWidget(caption)
        layout.addWidget(close_btn)


class StreamThread(QThread):
    """Poll adb for frames until stopped."""

    frame_ready = pyqtSignal(np.ndarray, int, int)
    status = pyqtSignal(str)

    def __init__(self, interval: float = 0.4, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._interval = max(interval, 0.05)
        self._running = True
        self._last_status = ""

    def stop(self) -> None:
        self._running = False

    def _sleep(self, seconds: float) -> None:
        """Sleep in small slices so stop() is honoured quickly."""
        deadline = time.monotonic() + seconds
        while self._running:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(0.05, remaining))

    def _report(self, message: str) -> None:
        if message != self._last_status:
            self._last_status = message
            self.status.emit(message)

    def run(self) -> None:  # noqa: D102 - Qt entry point
        if adb_client.adb_path() is None:
            self.status.emit("adb not found. Install android-tools-adb.")
            return

        failures = 0
        while self._running:
            started = time.monotonic()

            states = adb_client.device_states()
            if "device" not in states.values():
                if states:
                    detail = ", ".join(f"{serial}={state}" for serial, state in states.items())
                    self._report(f"Device not ready ({detail}). Accept the debugging prompt.")
                else:
                    self._report("No Android device found. Connect it and check 'adb devices'.")
                # Re-check periodically instead of spamming screencap.
                self._sleep(max(self._interval * 4, 1.0))
                continue

            frame = None
            data = adb_client.screencap()
            if data:
                decoded = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
                if decoded is not None:
                    frame = decoded

            if frame is not None:
                failures = 0
                height, width = frame.shape[:2]
                self._report(f"Streaming {width}x{height}")
                self.frame_ready.emit(frame, width, height)
            else:
                failures += 1
                if failures % 5 == 1:
                    self._report("Capture failed. Is the device connected and authorized?")

            self._sleep(self._interval - (time.monotonic() - started))


class AndroidMirrorApp(QMainWindow):
    def __init__(self, pair_url: str, interval: float = 0.4) -> None:
        super().__init__()
        self.setWindowTitle("Android mirror")

        self.pair_url = pair_url
        self.device_width, self.device_height = FALLBACK_DEVICE_SIZE
        self._last_frame: np.ndarray | None = None

        self.display_label = QLabel(self)
        self.display_label.setAlignment(Qt.AlignCenter)
        self.display_label.setMinimumSize(320, 480)
        self.display_label.mousePressEvent = self.on_screen_click

        screenshot_btn = QPushButton("Save screenshot", self)
        screenshot_btn.clicked.connect(self.save_screenshot)

        qr_btn = QPushButton("Show QR", self)
        qr_btn.clicked.connect(self.show_pairing_dialog)

        controls = QHBoxLayout()
        controls.addWidget(screenshot_btn)
        controls.addWidget(qr_btn)
        controls.addStretch(1)

        layout = QVBoxLayout()
        layout.addWidget(self.display_label, stretch=1)
        layout.addLayout(controls)

        container = QWidget(self)
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.resize(460, 900)

        self.statusBar().showMessage("Starting capture...")

        self.thread = StreamThread(interval, self)
        self.thread.frame_ready.connect(self.update_image)
        self.thread.status.connect(lambda text: self.statusBar().showMessage(text))
        self.thread.start()

    def show_pairing_dialog(self) -> None:
        QRDialog(self.pair_url, self).exec_()

    def update_image(self, cv_img: np.ndarray, orig_w: int, orig_h: int) -> None:
        self.device_width, self.device_height = orig_w, orig_h
        self._last_frame = cv_img

        rgb = np.ascontiguousarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))
        height, width, channels = rgb.shape
        image = QImage(
            rgb.data, width, height, channels * width, QImage.Format_RGB888
        ).copy()

        target = self.display_label.size()
        if target.width() < 50 or target.height() < 50:
            target.setWidth(400)
            target.setHeight(800)

        pixmap = QPixmap.fromImage(image).scaled(
            target, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.display_label.setPixmap(pixmap)
        self.setWindowTitle(f"Android mirror - {orig_w}x{orig_h}")

    def on_screen_click(self, event) -> None:
        pixmap = self.display_label.pixmap()
        if pixmap is None:
            return

        point = geometry.map_click(
            event.pos().x(),
            event.pos().y(),
            self.display_label.width(),
            self.display_label.height(),
            pixmap.width(),
            pixmap.height(),
            self.device_width,
            self.device_height,
        )
        if point is None:
            self.statusBar().showMessage("Click inside the mirrored screen to tap.", 3000)
            return

        x, y = point
        if adb_client.tap(x, y):
            self.statusBar().showMessage(f"Tap sent: {x}, {y}", 1500)
        else:
            self.statusBar().showMessage("Could not send tap. Is adb installed?", 3000)

    def save_screenshot(self) -> None:
        if self._last_frame is None:
            self.statusBar().showMessage("No frame captured yet.", 3000)
            return
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = Path.cwd() / f"screenshot-{stamp}.png"
        if cv2.imwrite(str(path), self._last_frame):
            self.statusBar().showMessage(f"Saved {path.name}", 4000)
        else:
            self.statusBar().showMessage(f"Could not write {path.name}", 4000)

    def closeEvent(self, event) -> None:
        self.thread.stop()
        self.thread.wait(3000)
        super().closeEvent(event)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mirror and control an Android device over adb.")
    parser.add_argument(
        "--url",
        help="URL to encode in the QR code (default: http://<lan-ip>:<port>)",
    )
    parser.add_argument("--host", help="Host used when building the QR URL")
    parser.add_argument(
        "--port",
        type=int,
        help=f"Pairing server port used in the QR URL (default: ${'PAIR_PORT'} or {settings.DEFAULT_PORT})",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.4,
        help="Seconds between screen captures (default: 0.4)",
    )
    parser.add_argument(
        "--no-qr",
        action="store_true",
        help="Skip the pairing QR dialog on launch",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    url = args.url or settings.pair_url(args.host, args.port)

    app = QApplication(sys.argv[:1])
    app.setApplicationName("android-mirror")

    window = AndroidMirrorApp(url, interval=args.interval)
    window.show()

    if not args.no_qr:
        window.show_pairing_dialog()

    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
