"""Small wrapper around the adb command line.

Every call degrades to a falsy result instead of raising, so the UI can report
a problem rather than crash.
"""

from __future__ import annotations

import shutil
import subprocess

ADB = "adb"


def adb_path() -> str | None:
    """Return the adb executable path, or None when it is not installed."""
    return shutil.which(ADB)


def device_states(timeout: float = 5.0) -> dict[str, str]:
    """Map serial -> state (device, unauthorized, offline, ...)."""
    if adb_path() is None:
        return {}
    try:
        result = subprocess.run(
            [ADB, "devices"], capture_output=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}
    states: dict[str, str] = {}
    for line in result.stdout.decode(errors="replace").splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2:
            states[parts[0]] = parts[1]
    return states


def devices(timeout: float = 5.0) -> list[str]:
    """Serials of devices that are connected and authorized."""
    return [serial for serial, state in device_states(timeout).items() if state == "device"]


def screencap(timeout: float = 15.0) -> bytes | None:
    """Grab one PNG frame from the device, or None on failure."""
    if adb_path() is None:
        return None
    try:
        result = subprocess.run(
            [ADB, "exec-out", "screencap", "-p"],
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0 or not result.stdout:
        return None
    return result.stdout


def tap(x: int, y: int) -> bool:
    """Send a tap without blocking the caller's thread."""
    if adb_path() is None:
        return False
    try:
        subprocess.Popen(
            [ADB, "shell", "input", "tap", str(int(x)), str(int(y))],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return False
    return True
