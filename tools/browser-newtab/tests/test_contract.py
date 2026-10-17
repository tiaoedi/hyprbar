"""Offline extension packaging contract; run with unittest discovery."""
import json
from pathlib import Path
import unittest
import tomllib

ROOT = Path(__file__).resolve().parents[1]


class Contract(unittest.TestCase):
    def test_local_mv3_override_with_search_only(self) -> None:
        self.assertTrue((ROOT / 'manifest.json').exists(), 'missing companion manifest')
        manifest = json.loads((ROOT / 'manifest.json').read_text())
        self.assertEqual(manifest['manifest_version'], 3)
        self.assertEqual(manifest['chrome_url_overrides'], {'newtab': 'newtab.html'})
        self.assertEqual(manifest['permissions'], ['search'])
        for forbidden in ('content_scripts', 'host_permissions', 'background', 'chrome_settings_overrides'):
            self.assertNotIn(forbidden, manifest)
        html = (ROOT / 'newtab.html').read_text()
        self.assertIn('lang="pt-BR"', html)
        self.assertNotRegex(html, r'<style|\sstyle=|\son\w+=|<script(?![^>]*src=)')
        self.assertNotRegex(html, r'https?://')
        for name in ('newtab.css', 'newtab.js', 'palette.css'):
            self.assertTrue((ROOT / name).is_file(), name)


    def test_template_integration_does_not_override_hooks(self) -> None:
        path = ROOT / 'browser-newtab.toml'
        self.assertTrue(path.is_file(), 'missing user-template integration')
        config = tomllib.loads(path.read_text())
        template = config['theme']['templates']['user']['browser_newtab']
        self.assertEqual(set(template), {'input_path', 'output_path'})
        self.assertEqual(template['input_path'], 'templates/browser-newtab/palette.css.in')
        self.assertEqual(template['output_path'], '~/.local/share/hyprbar/extensions/newtab/palette.css')
        self.assertNotIn('hooks', config)
        tokens = (ROOT / 'palette.css.in').read_text()
        for token in ('background', 'on_surface', 'surface_container', 'on_surface_variant', 'primary', 'on_primary', 'outline'):
            self.assertIn('{{colors.' + token + '.default.hex}}', tokens)


if __name__ == '__main__':
    unittest.main()
