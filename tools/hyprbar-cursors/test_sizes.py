#!/usr/bin/env python3
"""Regression: Xcursor must load the requested size, not a 48px fallback."""
import ctypes as C
import pathlib
import unittest

class Image(C.Structure):
    _fields_ = [(name, C.c_uint) for name in
                ('version', 'size', 'width', 'height', 'xhot', 'yhot', 'delay')] + [('pixels', C.c_void_p)]

class CursorSizeTests(unittest.TestCase):
    def test_each_shape_loads_at_requested_size(self):
        lib = C.CDLL('libXcursor.so.1')
        lib.XcursorFilenameLoadImage.argtypes = [C.c_char_p, C.c_int]
        lib.XcursorFilenameLoadImage.restype = C.POINTER(Image)
        lib.XcursorImageDestroy.argtypes = [C.POINTER(Image)]
        root = pathlib.Path(__file__).resolve().parent / 'hyprbar' / 'cursors'
        for path in sorted(root.iterdir()):
            for size in (24, 32, 48):
                with self.subTest(shape=path.name, size=size):
                    image = lib.XcursorFilenameLoadImage(str(path).encode(), size)
                    self.assertTrue(image)
                    try:
                        self.assertEqual((image.contents.size, image.contents.width, image.contents.height),
                                         (size, size, size))
                        self.assertLess(image.contents.xhot, size)
                        self.assertLess(image.contents.yhot, size)
                    finally:
                        lib.XcursorImageDestroy(image)

if __name__ == '__main__':
    unittest.main()
