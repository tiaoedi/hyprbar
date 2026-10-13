#!/usr/bin/env python3
"""The bundled icon must contain the maintainer-provided JPEG, not a home path."""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_LOGO_SHA256 = "d567f83ff2852d74856720d42e64913344c2be811a2429f601d67385ea7ef33b"


class HyprbarLogoTest(unittest.TestCase):
    def test_svg_embeds_the_exact_provided_logo(self) -> None:
        svg = ET.parse(ROOT / "assets/hyprbar.svg").getroot()
        images = svg.findall("{http://www.w3.org/2000/svg}image")
        self.assertEqual(len(images), 1, "Hyprbar icon must embed the provided image")
        source = images[0].get("href") or images[0].get("{http://www.w3.org/1999/xlink}href", "")
        self.assertTrue(source.startswith("data:image/jpeg;base64,"))
        image = base64.b64decode(source.split(",", 1)[1], validate=True)
        self.assertEqual(hashlib.sha256(image).hexdigest(), EXPECTED_LOGO_SHA256)
        self.assertEqual(svg.get("viewBox"), "0 0 600 600")
        self.assertNotIn("/home/", (ROOT / "assets/hyprbar.svg").read_text())


if __name__ == "__main__":
    unittest.main()
