#!/usr/bin/python3
"""Acceptance checks; run with /usr/bin/python3 -m unittest -v."""
import configparser
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
THEME = ROOT / 'hyprbar'

class ThemeTests(unittest.TestCase):
    def test_unique_canonical_artwork(self):
        import hashlib
        manifest = json.loads((ROOT / 'manifest.json').read_text())
        hashes = [hashlib.sha256((THEME / r['path']).read_bytes()).hexdigest() for r in manifest['canonical']]
        self.assertEqual(len(hashes), len(set(hashes)), 'each canonical SVG must be distinct artwork')

    def test_render_and_lookup_verifier(self):
        self.assertTrue((ROOT / 'verify.py').exists(), 'renderer and isolated GTK verifier required')
        import subprocess
        result = subprocess.run(['/usr/bin/python3', str(ROOT / 'verify.py')], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads((ROOT / 'verification.json').read_text())
        self.assertEqual(report['render_count'], report['canonical'] * 4)
        self.assertEqual(report['lookup_count'], report['svg_entries'] * 4)
        self.assertTrue(report['symbolic_inherited'])
        self.assertTrue(Path(report['preview']).exists())
        import struct
        width, height = struct.unpack('>II', Path(report['size_preview']).read_bytes()[16:24])
        self.assertGreaterEqual(width, 700)
        self.assertGreaterEqual(height, 700, 'size strip must show 128px artwork unscaled')
        self.assertTrue((ROOT / 'README.md').exists())
        self.assertTrue((THEME / 'LICENSE').exists())

    def test_generated_theme_contract(self):
        self.assertTrue((ROOT / 'manifest.json').exists(), 'generator must emit manifest.json')
        manifest = json.loads((ROOT / 'manifest.json').read_text())
        canonical, aliases = manifest['canonical'], manifest['aliases']
        self.assertTrue(50 <= len(canonical) <= 80)
        self.assertEqual(manifest['totals'], {'canonical': len(canonical), 'aliases': len(aliases), 'svg_entries': len(canonical)+len(aliases)})
        paths = [r['path'] for r in canonical+aliases]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertEqual(set(paths), {str(p.relative_to(THEME)) for p in THEME.rglob('*.svg')})
        parser = configparser.ConfigParser()
        parser.read(THEME / 'index.theme')
        self.assertEqual(parser['Icon Theme']['Name'], 'hyprbar')
        self.assertEqual(parser['Icon Theme']['Inherits'], 'Adwaita,hicolor')
        for directory in parser['Icon Theme']['Directories'].split(','):
            self.assertEqual(parser[directory]['Type'], 'Scalable')
            contexts = {'apps':'Applications','devices':'Devices','mimetypes':'MimeTypes','places':'Places'}
            self.assertEqual(parser[directory]['Context'], contexts[Path(directory).name])
            self.assertTrue((THEME / directory).is_dir())
        for record in canonical:
            p = THEME / record['path']
            self.assertFalse(p.is_symlink())
            root = ET.parse(p).getroot()
            self.assertEqual(root.attrib['viewBox'], '0 0 128 128')
            for el in root.iter():
                self.assertNotIn(el.tag.split('}')[-1], ['script','text','image','foreignObject','use'])
                for key, value in el.attrib.items():
                    self.assertNotIn('href', key)
                    self.assertNotIn('http:', value)
                    self.assertNotIn('https:', value)
                    if 'url(' in value:
                        self.assertTrue(value.startswith('url(#'))
            self.assertNotIn('-symbolic', p.name)
        for record in aliases:
            p = THEME / record['path']
            self.assertTrue(p.is_symlink())
            self.assertTrue(p.exists())
            self.assertTrue(p.resolve().is_relative_to(THEME.resolve()))
            self.assertEqual(str(p.resolve().relative_to(THEME)), record['target'])
        forbidden = ('apple', 'finder', 'safari', 'macintosh')
        self.assertFalse(any(word in p.lower() for p in paths for word in forbidden))
        self.assertFalse(any('-symbolic' in p for p in paths))
        required = ['org.gnome.Nautilus','system-file-manager','hyprbar','google-chrome','brave-browser','firefox','kitty','utilities-terminal','code','vlc','com.obsproject.Studio','gimp','libreoffice-writer','libreoffice-calc','libreoffice-impress','libreoffice-draw','libreoffice-startcenter','org.telegram.desktop','discord','bitwarden','brave-gneipglanmgpdhiohiogfnhdpoaafoob-Default','org.pulseaudio.pavucontrol']
        names = {Path(p).stem for p in paths}
        self.assertTrue(set(required) <= names, set(required)-names)

if __name__ == '__main__':
    unittest.main()
