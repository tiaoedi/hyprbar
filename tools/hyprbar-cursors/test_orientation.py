#!/usr/bin/env python3
"""Column resizing is horizontal; row resizing is vertical in both formats."""
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import zipfile

from PIL import Image
import generate
from test_pixels import frames

ROOT = Path(__file__).resolve().parent


class OrientationTests(unittest.TestCase):
    def assert_orientation(self, name, alpha):
        box = alpha.point(lambda a: 255 if a >= 128 else 0).getbbox()
        self.assertIsNotNone(box)
        width, height = box[2] - box[0], box[3] - box[1]
        if name == 'col-resize':
            self.assertGreater(width, height, 'column resize arrows must be horizontal')
        else:
            self.assertGreater(height, width, 'row resize arrows must be vertical')

    def svg_alpha(self, svg):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'cursor.svg'
            path.write_bytes(svg)
            rgba = subprocess.check_output(['magick', '-background', 'none', str(path),
                                            '-depth', '8', 'rgba:-'])
        return Image.frombytes('RGBA', (48, 48), rgba).getchannel('A')

    def test_generator_svg_orientation(self):
        for name in ('col-resize', 'row-resize'):
            with self.subTest(shape=name):
                body = generate.SVG[name][0]
                svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48">{body}</svg>'
                self.assert_orientation(name, self.svg_alpha(svg.encode()))

    def test_hyprcursor_svg_orientation(self):
        for name in ('col-resize', 'row-resize'):
            with self.subTest(shape=name):
                with zipfile.ZipFile(ROOT / 'hyprbar' / 'hyprcursors' / name) as archive:
                    self.assert_orientation(name, self.svg_alpha(archive.read('image.svg')))

    def test_xcursor_orientation_at_every_size(self):
        for name in ('col-resize', 'row-resize'):
            raw = (ROOT / 'hyprbar' / 'cursors' / name).read_bytes()
            for size, start in frames(raw):
                with self.subTest(shape=name, size=size):
                    pixels = struct.unpack_from(f'<{size * size}I', raw, start)
                    alpha = Image.frombytes('L', (size, size), bytes(p >> 24 for p in pixels))
                    self.assert_orientation(name, alpha)


if __name__ == '__main__':
    unittest.main()
