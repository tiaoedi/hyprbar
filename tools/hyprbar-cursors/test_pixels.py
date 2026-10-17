#!/usr/bin/env python3
"""Regressions for premultiplied Xcursor pixels and straight-alpha previews."""
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

from PIL import Image
import generate

ROOT = Path(__file__).resolve().parent


def frames(raw):
    count = struct.unpack_from('<I', raw, 12)[0]
    for index in range(count):
        _, size, offset = struct.unpack_from('<III', raw, 16 + 12 * index)
        yield size, offset + 36


class PixelTests(unittest.TestCase):
    def test_generator_premultiplies_rgb(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'cursor'
            generate.xcursor_chunk('test', '<rect width="48" height="48" fill="#ff8040" fill-opacity="0.5"/>', 0, 0, path)
            raw = path.read_bytes()
            for size, start in frames(raw):
                with self.subTest(size=size):
                    pixel = struct.unpack_from('<I', raw, start + 4 * (size * (size // 2) + size // 2))[0]
                    a, r, g, b = pixel >> 24, (pixel >> 16) & 255, (pixel >> 8) & 255, pixel & 255
                    self.assertTrue(0 < a < 255)
                    self.assertEqual((r, g, b), (a, (128 * a + 127) // 255, (64 * a + 127) // 255))

    def test_all_generated_pixels_are_premultiplied(self):
        for path in sorted((ROOT / 'hyprbar' / 'cursors').iterdir()):
            if path.is_symlink():
                continue
            raw = path.read_bytes()
            for size, start in frames(raw):
                with self.subTest(shape=path.name, size=size):
                    pixels = struct.unpack_from(f'<{size * size}I', raw, start)
                    invalid = sum(max((p >> 16) & 255, (p >> 8) & 255, p & 255) > p >> 24 for p in pixels)
                    self.assertEqual(invalid, 0, 'RGB channels must not exceed alpha (including alpha=0)')


class VerifierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copy2(ROOT / 'verify.py', self.root)
        shutil.copytree(ROOT / 'hyprbar', self.root / 'hyprbar', symlinks=True)
        self.cursor = self.root / 'hyprbar' / 'cursors' / 'alias'

    def verify(self):
        return subprocess.run([sys.executable, str(self.root / 'verify.py')],
                              capture_output=True, text=True,
                              env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})

    def test_verifier_rejects_nonpremultiplied_pixels_at_every_size(self):
        original = self.cursor.read_bytes()
        for size, start in frames(original):
            for pixel in (0x00010000, 0x01000200):
                with self.subTest(size=size, pixel=hex(pixel)):
                    raw = bytearray(original)
                    struct.pack_into('<I', raw, start, pixel)
                    self.cursor.write_bytes(raw)
                    result = self.verify()
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertIn('premultiplied', result.stderr)

    def test_preview_unpremultiplies_before_pillow_compositing(self):
        raw = bytearray(self.cursor.read_bytes())
        for size, start in frames(raw):
            if size == 48:
                struct.pack_into('<II', raw, start, 0, 0x80402010)
        self.cursor.write_bytes(raw)
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stderr)
        with Image.open(self.root / 'previews' / 'contact-sheet.png') as sheet:
            expected = Image.new('RGBA', (1, 1), (239, 242, 247, 255))
            expected.alpha_composite(Image.new('RGBA', (1, 1), (128, 64, 32, 128)))
            self.assertEqual(sheet.getpixel((17, 8)), expected.getpixel((0, 0)))
            self.assertEqual(sheet.getpixel((16, 8)), (239, 242, 247, 255))


if __name__ == '__main__':
    unittest.main()
