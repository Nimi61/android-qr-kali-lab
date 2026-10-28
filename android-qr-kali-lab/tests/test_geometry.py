"""Unit tests for the click-to-device coordinate mapping."""

from __future__ import annotations

import unittest

import geometry


class MapClickTests(unittest.TestCase):
    def test_pixmap_fills_label(self):
        self.assertEqual(
            geometry.map_click(50, 100, 400, 800, 400, 800, 1080, 1920),
            (135, 240),
        )

    def test_letterboxed_pixmap_is_offset(self):
        # 400px pixmap centred in a 500px wide label adds 50px of padding.
        self.assertEqual(
            geometry.map_click(50, 0, 500, 800, 400, 800, 400, 800),
            (0, 0),
        )
        # Pixmap spans x=50..449 inside the label; the last pixel maps to 399.
        self.assertEqual(
            geometry.map_click(449, 799, 500, 800, 400, 800, 400, 800),
            (399, 799),
        )

    def test_click_on_padding_returns_none(self):
        self.assertIsNone(geometry.map_click(10, 100, 500, 800, 400, 800, 1080, 1920))
        self.assertIsNone(geometry.map_click(450, 100, 500, 800, 400, 800, 1080, 1920))

    def test_bottom_right_is_clamped_inside_screen(self):
        point = geometry.map_click(399, 799, 400, 800, 400, 800, 1080, 1920)
        self.assertEqual(point, (1077, 1917))
        x, y = point
        self.assertLess(x, 1080)
        self.assertLess(y, 1920)

    def test_invalid_dimensions_return_none(self):
        self.assertIsNone(geometry.map_click(10, 10, 100, 100, 0, 100, 1080, 1920))
        self.assertIsNone(geometry.map_click(10, 10, 100, 100, 100, 100, 0, 0))


if __name__ == "__main__":
    unittest.main()
