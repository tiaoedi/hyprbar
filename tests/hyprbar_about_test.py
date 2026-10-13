#!/usr/bin/env python3
"""Focused native About integration and branding-provenance regression checks."""
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(sys.argv.pop(1)) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]


class AboutIntegrationTest(unittest.TestCase):
    def test_about_is_an_always_visible_native_section(self) -> None:
        header = (ROOT / "src/shell/settings/settings_registry.h").read_text()
        registry = (ROOT / "src/shell/settings/settings_registry.cpp").read_text()
        self.assertRegex(header, r"\bAbout\s*,")
        self.assertRegex(registry, r'\{SettingsSection::About,\s*"about",\s*"info-circle",\s*true,\s*true\}')

    def test_about_content_is_wired_to_renderer_and_title_host(self) -> None:
        component = ROOT / "src/shell/settings/settings_content_about.cpp"
        self.assertTrue(component.is_file(), "native About builder is missing")
        source = component.read_text()
        for token in ('paths::assetPath("hyprbar.svg")', 'build_info::displayVersion()',
                      'about::developer', 'about::links', 'net::openInBrowser(url)', 'ui::button(',
                      'ctx.pageTitleRow', 'ctx.contentScale', 'ctx.uiScale'):
            self.assertIn(token, source)
        self.assertIn('[url = std::string(link.url)]', source)
        self.assertNotIn('[this]', source)
        scene = (ROOT / "src/shell/settings/settings_window_scene.cpp").read_text()
        self.assertRegex(scene, r'if \(m_selectedSection == "about" && m_surface != nullptr\)')
        for token in ('settings::addSettingsAbout(', '.renderer = m_surface->renderTarget().renderer()',
                      '.contentScale = scale * m_surface->effectiveBufferScale()', '.uiScale = scale', '.pageTitleRow = m_pageTitleRow'):
            self.assertIn(token, scene)
        generic = (ROOT / "src/shell/settings/settings_content.cpp").read_text()
        self.assertRegex(generic, r'visibleEntries == 0[^\n]*ctx.selectedSection != "about"')
        meson = (ROOT / "meson.build").read_text()
        for token in ('src/shell/settings/settings_content_about.cpp', "'settings_about'", "'hyprbar_about_metadata'"):
            self.assertIn(token, meson)

    def test_about_translations_credit_origin_and_mit(self) -> None:
        for filename, title, provenance in (
            ("en.json", "About", "Hyprbar is an independent fork based on Noctalia v5.2.1."),
            ("pt-BR.json", "Sobre", "Hyprbar é um fork independente baseado no Noctalia v5.2.1."),
        ):
            document = json.loads((ROOT / "assets/translations" / filename).read_text())
            self.assertTrue("about" in document["settings"], f"{filename}: About translations are missing")
            about = document["settings"]["about"]
            self.assertEqual(document["settings"]["navigation"]["sections"]["about"], title)
            self.assertEqual(about["provenance"], provenance)
            self.assertIn("MIT", about["license"])
            self.assertIn("{name}", about["developer"])
            self.assertIn("{version}", about["version"])
            self.assertEqual(about["youtube"], "YouTube — Linux Livre")
            for key in ("developer-profile", "project"):
                self.assertTrue(about[key])

    def test_provenance_allowance_is_exact_and_does_not_hide_branding(self) -> None:
        spec = importlib.util.spec_from_file_location("branding", ROOT / "tests/hyprbar_branding_test.py")
        assert spec is not None and spec.loader is not None
        branding = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(branding)
        check = getattr(branding, "unexpected_translation_branding", None)
        self.assertIsNotNone(check, "branding guard needs a narrowly scoped provenance check")
        assert check is not None
        key = "settings.about.provenance"
        for filename, text in (
            ("en.json", "Hyprbar is an independent fork based on Noctalia v5.2.1."),
            ("pt-BR.json", "Hyprbar é um fork independente baseado no Noctalia v5.2.1."),
        ):
            self.assertFalse(check(filename, key, text))
            self.assertTrue(check(filename, "settings.window.title", text))
            self.assertTrue(check(filename, "settings.about.developer-profile", "Noctalia"))
            self.assertTrue(check(filename, key, text + " Welcome to Noctalia!"))
            self.assertTrue(check(filename, key, text.replace("v5.2.1", "v5.3.0")))
            self.assertTrue(check("fr.json", key, text))
        self.assertFalse(check("en.json", "settings.window.title", "Hyprbar"))
        self.assertFalse(check("en.json", "settings.window.title", "noctalia-shell"))
        guard = (ROOT / "tests/hyprbar_branding_test.py").read_text()
        self.assertIn("unexpected_translation_branding(source.name, key_path, text)", guard)


if __name__ == "__main__":
    unittest.main()
