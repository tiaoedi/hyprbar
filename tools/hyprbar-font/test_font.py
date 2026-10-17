import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent
SOURCE = Path('/usr/share/fonts/adwaita-sans-fonts')

class HyprbarFontTest(unittest.TestCase):
    def test_family_and_original_glyphs_are_preserved(self):
        self.assertTrue((ROOT/'build_font.py').is_file(), 'Hyprbar font builder is missing')
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([sys.executable, str(ROOT/'build_font.py'), '--output', tmp], check=True)
            for style in ('Regular', 'Italic'):
                original = TTFont(SOURCE/f'AdwaitaSans-{style}.ttf')
                font = TTFont(Path(tmp)/f'Hyprbar-{style}.ttf', checkChecksums=2)
                for table in font.keys():
                    if table != 'GlyphOrder':
                        font[table]  # force table/checksum validation
                for nid in (1, 16):
                    self.assertEqual(font['name'].getDebugName(nid), 'Hyprbar')
                self.assertEqual(font['name'].getDebugName(6), 'Hyprbar' + ('-Italic' if style=='Italic' else ''))
                self.assertEqual(font.getBestCmap(), original.getBestCmap())
                self.assertEqual(font.getGlyphOrder(), original.getGlyphOrder())
                self.assertEqual([(a.axisTag,a.minValue,a.defaultValue,a.maxValue) for a in font['fvar'].axes], [(a.axisTag,a.minValue,a.defaultValue,a.maxValue) for a in original['fvar'].axes])
                for char in 'Hyprbar São João çãéêõ€':
                    self.assertIn(ord(char),font.getBestCmap())
                self.assertIn('Inter Project Authors',font['name'].getDebugName(0))
                self.assertIn('Open Font License',font['name'].getDebugName(13))
            self.assertEqual((Path(tmp)/'OFL.txt').read_bytes(), Path('/usr/share/licenses/adwaita-sans-fonts/LICENSE').read_bytes())

if __name__=='__main__':
    unittest.main()
