
import sys
import subprocess
import numpy as np
import cv2
import qrcode
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QDialog
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QImage, QPixmap

# --- QR Code Display Window ---
class QRDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pair Android Device")
        
        # QR content (e.g. WiFi ADB pairing payload or device handshake token)
        data = "http://192.168.1.215:8765"
        qr_img = qrcode.make(data)
        qr_img.save("temp_qr.png")

        layout = QVBoxLayout()
        label = QLabel(self)
        label.setPixmap(QPixmap("temp_qr.png"))
        layout.addWidget(label)
        
        close_btn = QPushButton("Done / Connected", self)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)

# --- Background Frame Capture Thread ---
class StreamThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray, int, int)

    def run(self):
        while True:
            # Execute screen capture over ADB stream
            cmd = ["adb", "exec-out", "screencap", "-p"]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            screen_bytes, _ = proc.communicate()

            if not screen_bytes:
                continue

            # Decode raw stream bytes to OpenCV image format
            img_array = np.frombuffer(screen_bytes, dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            if frame is not None:
                height, width, _ = frame.shape
                self.change_pixmap_signal.emit(frame, width, height)

# --- Main Interface & Control Window ---
class AndroidMirrorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kali Custom ADB Screen Controller")
        
        self.device_width = 1080  # Default fallback dimensions
        self.device_height = 1920

        # UI Setup
        self.display_label = QLabel(self)
        self.display_label.setAlignment(Qt.AlignCenter)
        self.display_label.mousePressEvent = self.on_screen_click

        container = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.display_label)
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Show QR Dialog on launch
        qr_popup = QRDialog(self)
        qr_popup.exec_()

        # Start Screen Capture
        self.thread = StreamThread()
        self.thread.change_pixmap_signal.connect(self.update_image)
        self.thread.start()

    def update_image(self, cv_img, orig_w, orig_h):
        self.device_width = orig_w
        self.device_height = orig_h

        # Convert OpenCV BGR format to RGB Qt Pixmap
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # Scale to window bounds
        scaled_pixmap = QPixmap.fromImage(convert_to_Qt_format).scaled(
            400, 800, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.display_label.setPixmap(scaled_pixmap)

    def on_screen_click(self, event):
        # Translate QT UI coordinates to actual device pixel coordinates
        pixmap = self.display_label.pixmap()
        if not pixmap:
            return

        click_x = event.pos().x()
        click_y = event.pos().y()

        # Calculate translation ratio
        target_x = int((click_x / pixmap.width()) * self.device_width)
        target_y = int((click_y / pixmap.height()) * self.device_height)

        # Send tap input command over ADB
        subprocess.Popen(["adb", "shell", "input", "tap", str(target_x), str(target_y)])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AndroidMirrorApp()
    window.show()
    sys.exit(app.exec_())
