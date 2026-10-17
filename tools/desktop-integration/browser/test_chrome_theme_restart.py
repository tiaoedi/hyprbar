"""Regression checks for Chromium theme-cache invalidation; no real browsers."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("chrome_theme_restart", Path(__file__).with_name("chrome-theme-restart.py"))
hook = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = hook
spec.loader.exec_module(hook)


class ThemeCacheTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paths = hook.Paths(
            user_data_dir=self.root / "profile", default_user_data_dir=self.root / "profile",
            theme_dir=self.root / "theme", manifest=self.root / "theme/manifest.json",
            state_dir=self.root / "state", proc_dir=self.root / "proc",
            chrome_binary=self.root / "browser", chrome_launcher=self.root / "launcher",
            browser_name="Test", browser_slug="test",
        )
        self.paths.theme_dir.mkdir()
        self.paths.manifest.write_text('{"theme": {}}')
        self.cache = self.paths.theme_dir / "Cached Theme.pak"

    def restart(self, stopped=True):
        def launch(*args, **kwargs):
            self.assertFalse(self.cache.exists(), "stale theme cache survives browser relaunch")
        with patch.object(hook.os, "kill"), patch.object(hook, "_wait_until_stopped", return_value=stopped), patch.object(hook.subprocess, "Popen", side_effect=launch) as popen, patch.object(hook, "chrome_main_pids", return_value=[987654]):
            result = hook._restart(self.paths, "Default", [987653])
            return result, popen.call_count

    def test_stale_cache_removed_before_relaunch(self):
        self.cache.write_bytes(b"old palette")
        self.assertEqual(self.restart(), (True, 1))
        self.assertEqual(self.paths.manifest.read_text(), '{"theme": {}}')

    def test_missing_cache_is_safe(self):
        self.assertEqual(self.restart(), (True, 1))

    def test_shutdown_timeout_preserves_cache(self):
        self.cache.write_bytes(b"old palette")
        self.assertEqual(self.restart(stopped=False), (False, 0))
        self.assertEqual(self.cache.read_bytes(), b"old palette")

    def test_closed_browser_invalidates_cache_without_launching(self):
        self.paths.state_dir.mkdir()
        state_file = self.paths.state_dir / "test-theme-restart.sha256"
        state_file.write_text("old digest\n")
        self.cache.write_bytes(b"old palette")
        with patch.object(hook, "configured_paths", return_value=self.paths), patch.object(hook, "active_theme_profiles", return_value=("Default", ["Default"])), patch.object(hook, "chrome_main_pids", return_value=[]), patch.object(hook.subprocess, "Popen") as popen:
            self.assertEqual(hook.run(), 0)
            popen.assert_not_called()
        self.assertFalse(self.cache.exists(), "closed browser would reuse stale cache on next start")
        self.assertEqual(state_file.read_text().strip(), hook.manifest_digest(self.paths.manifest))

    def test_cache_unlink_error_aborts_relaunch(self):
        self.cache.mkdir()
        self.assertEqual(self.restart(), (False, 0))


if __name__ == "__main__":
    unittest.main()
