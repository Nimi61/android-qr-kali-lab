"""Coordinate translation between the widget and the device screen.

Pure functions only, so this can be unit tested without a display.
"""

from __future__ import annotations


def map_click(
    click_x: float,
    click_y: float,
    label_w: int,
    label_h: int,
    pixmap_w: int,
    pixmap_h: int,
    device_w: int,
    device_h: int,
) -> tuple[int, int] | None:
    """Translate a click on a centred pixmap into device pixel coordinates.

    The pixmap is letterboxed inside the label, so the offset has to be removed
    before scaling. Returns None when the click landed on empty label space or
    when any dimension is unusable.
    """
    if min(label_w, label_h, pixmap_w, pixmap_h, device_w, device_h) <= 0:
        return None

    offset_x = max((label_w - pixmap_w) / 2, 0.0)
    offset_y = max((label_h - pixmap_h) / 2, 0.0)

    local_x = click_x - offset_x
    local_y = click_y - offset_y

    if not (0 <= local_x < pixmap_w and 0 <= local_y < pixmap_h):
        return None

    device_x = int(local_x / pixmap_w * device_w)
    device_y = int(local_y / pixmap_h * device_h)

    # Stay inside the screen, even after truncation.
    return min(device_x, device_w - 1), min(device_y, device_h - 1)
