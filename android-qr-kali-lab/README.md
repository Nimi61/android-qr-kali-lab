# android-qr-kali-lab

A small Kali Linux lab for pairing with an Android device over a QR code, mirroring its
screen on the desktop, and tapping on the mirror to control the phone through ADB.

Built for learning and experimentation on your own devices. It is not a hardened tool and
does not implement real Android wireless-debugging pairing; see [Security](#security) and
[Limitations](#limitations).

---

## Features

- **Live screen mirror** in a PyQt5 window, refreshed from `adb exec-out screencap -p`
- **Click to tap** - mouse clicks are translated to device pixel coordinates and sent with
  `adb shell input tap`, with correct handling of letterboxing when the window is resized
- **QR pairing page** served by a small threaded HTTP server, with optional shared token
- **No dumped temp files**: QR codes are generated in memory, and screenshots only when you
  ask for them
- **Graceful device handling**: clear status messages for missing `adb`, no device,
  unauthorized device, and failed captures
- **Unit-tested coordinate math** that runs without a display

## Repository layout

```
.
├── mirror_app.py      # PyQt5 mirror + tap control window
├── pair_server.py     # HTTP server for the pairing page
├── index.html         # mobile pairing page (served by pair_server.py)
├── screen_now.py      # standalone QR generator
├── settings.py        # LAN IP detection, port/URL helpers
├── adb_client.py      # thin, non-raising wrapper around adb
├── geometry.py        # click -> device coordinate mapping
├── tests/             # unittest suite for geometry.py
├── requirements.txt
└── LICENSE            # MIT
```

## Requirements

- Kali Linux or another Debian-based distro with a desktop session
- Python 3.10+
- `adb` from `android-tools-adb`
- Android device with **USB debugging** enabled and the host key accepted

```bash
sudo apt install android-tools-adb python3-venv
```

## Setup

```bash
git clone https://github.com/Nimi61/android-qr-kali-lab.git
cd android-qr-kali-lab
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

If `pip` is missing inside the venv, bootstrap it once:

```bash
python3 -m ensurepip --upgrade
pip install -r requirements.txt
```

> On Kali, `apt upgrade` can move `/usr/bin/python3` to a new minor version and leave an
> existing venv pointing at the wrong interpreter, which shows up as missing packages.
> Create a fresh venv with the current `python3`, or repoint `venv/bin/python3` at the
> interpreter the venv was built with.

The requirements use `opencv-python-headless`, because the GUI is PyQt5. Installing the
Qt-bundling `opencv-python` alongside PyQt5 can cause `xcb` plugin conflicts.

## Usage

### 1. Mirror and control the device

```bash
source venv/bin/activate
adb devices                 # must show your device as "device", not "unauthorized"
python3 mirror_app.py
```

A QR dialog opens on launch with the pairing URL. Dismiss it with **Done / Connected** to
start mirroring. Buttons under the screen:

- **Save screenshot** writes `screenshot-YYYYmmdd-HHMMSS.png` in the current directory
- **Show QR** reopens the pairing dialog

Clicking anywhere on the mirrored image sends a tap; clicks on the empty padding around the
image are ignored.

Options:

```bash
python3 mirror_app.py --url http://192.168.1.50:8765   # exact QR payload
python3 mirror_app.py --host 192.168.1.50 --port 8765  # build it from parts
python3 mirror_app.py --interval 0.2                   # faster refresh (default 0.4s)
python3 mirror_app.py --no-qr                          # skip the dialog
```

If the device is missing, the status bar says so and the capture thread waits and re-checks
once a second instead of spinning.

### 2. Serve the pairing page

```bash
source venv/bin/activate
python3 pair_server.py
```

Output:

```
Pairing server listening on 0.0.0.0:8765
Open http://192.168.1.50:8765/ on the phone, or scan the QR code in mirror_app.py
Ctrl+C to stop.
```

Endpoints:

| Method | Path | Behaviour |
| --- | --- | --- |
| GET | `/` , `/index.html` | Pairing page |
| GET | `/health` | `{"status": "ok"}` |
| POST | `/pair` | Logs the request, returns `{"status": "paired"}` |

Options:

```bash
python3 pair_server.py --port 9000
python3 pair_server.py --token mysecret    # rejects POST /pair without X-Pair-Token
python3 pair_server.py --host 127.0.0.1    # localhost only
python3 pair_server.py --quiet             # no per-request log lines
```

With a token, open the page as `http://<kali-ip>:<port>/?token=mysecret`. Tokenized requests
are also honoured by `mirror_app.py` if you include the token in `--url`.

### 3. Generate a QR code

```bash
python3 screen_now.py "https://kali.org" -o kali.png --show
```

Writes a PNG QR code and optionally opens it with your default viewer.

## Configuration

| Setting | Env var | Flag | Default |
| --- | --- | --- | --- |
| Pairing port | `PAIR_PORT` | `--port` | `8765` |
| Pairing token | `PAIR_TOKEN` | `--token` | none |
| Bind address | - | `--host` | `0.0.0.0` (server) |
| QR URL | - | `--url` / `--host` | `http://<lan-ip>:8765` |
| Capture interval | - | `--interval` | `0.4` seconds |

`settings.lan_ip()` picks the interface the machine would route through, so the QR code
usually points at the right address without editing any file.

## How it works

```
                    scan QR (http://<kali-ip>:8765)
  Android phone  ─────────────────────────────────────▶  index.html
        │                                                      │
        │  POST /pair  (+ X-Pair-Token)                        │
        ▼                                                      ▼
   pair_server.py                                logs the request, replies "paired"

  Android device  ──── adb exec-out screencap -p ────▶  mirror_app.py  (PyQt5)
  Android device  ◀─── adb shell input tap x y ───────        ▲
                                                       mouse click
```

The mirror and the pairing page are independent: mirroring works without the server, and the
server never touches ADB.

Click mapping (`geometry.py`) removes the letterbox offset, scales into device pixels, and
clamps to `device_width - 1` / `device_height - 1` so taps never land off-screen.

## Tests

```bash
source venv/bin/activate
python -m unittest discover -v
```

`tests/test_geometry.py` covers direct mapping, letterboxed mapping, clicks on padding,
edge clamping, and invalid dimensions. No display or device is needed.

## Troubleshooting

**`ModuleNotFoundError: No module named 'numpy'`**
The venv is active but dependencies are missing, or `pip` was absent. Inside the venv run
`python3 -m ensurepip --upgrade` then `pip install -r requirements.txt`.

**Mirror is blank or stuck on "No Android device found"**
`adb devices` must list the device as `device`. If it says `unauthorized`, accept the USB
debugging prompt on the phone. Verify capture directly with
`adb exec-out screencap -p > /tmp/s.png`.

**`Could not load the Qt platform plugin "xcb"`**
Usually a mix of Qt from `opencv-python` and PyQt5. Uninstall `opencv-python` and install
`opencv-python-headless`.

**Clicks land slightly off**
Mapping assumes the pixmap is centred in the label, which is how Qt lays it out. Keep the
default window size for best accuracy; extreme aspect ratios reduce precision.

**Nothing appears over SSH**
This is a GUI app. Use X11 forwarding or run it in the desktop session;
`QT_QPA_PLATFORM=offscreen` only verifies startup.

## Security

This is a lab project. Deliberately not included:

- TLS: the page and QR payload are plain HTTP
- Real authentication: the optional token is a shared secret, not user accounts
- Real ADB pairing: nothing calls `adb pair`; the "paired" response is cosmetic
- Access control on `--host 0.0.0.0` (the default): anyone on your LAN can load the page

Run it on a trusted network, stop the server when done, and never port-forward `8765`.
ADB itself grants full shell access to the device, so disable USB debugging when you are not
using this.

## Limitations

- Taps only; no swipes, long-press, scrolling, or keyboard input
- Full-frame PNG capture per refresh, so latency is not suitable for gaming
- Works with the single default ADB device; no `--serial` selection yet
- `opencv-python-headless` means no `cv2.imshow` debugging windows

## Roadmap

- `--serial` / device picker for multiple devices
- Swipe and long-press gestures
- Persistent settings file and a real `adb pair` flow
- CI job that runs the unit tests

## License

MIT - see [LICENSE](LICENSE). Copyright (c) 2026 Oluwapelumi (Nimi61).
