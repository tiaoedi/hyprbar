"""Regressions for menu-launched palette IPC and live theme updates."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import palette


class MenuPaletteTests(unittest.TestCase):
    def test_menu_path_without_local_bin_still_reads_selected_palette(self):
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as tmp:
            home = Path(tmp)
            executable = home / '.local/bin/hyprbar'
            executable.parent.mkdir(parents=True)
            executable.write_text('#!/bin/sh\ncase "$2" in\ncolor-scheme-get) echo "community First Theme";;\ntheme-mode-get) echo dark;;\nesac\n')
            executable.chmod(0o755)
            base = home / '.local/state/hyprbar/community-palettes'
            base.mkdir(parents=True)
            theme = base / 'First%20Theme.json'
            theme.write_text(json.dumps({'dark': {'mPrimary': '#123456', 'mSurface': '#101112'}}))
            env = {'HOME': str(home), 'PATH': '/usr/bin:/bin'}
            with patch.dict(os.environ, env, clear=True):
                first = palette.current()
                self.assertFalse(first['fallback'], 'Menu PATH must not silently select the fallback palette')
                self.assertEqual(first['colors']['mPrimary'], '#123456')
                # The same running process must notice an updated palette.
                theme.write_text(json.dumps({'dark': {'mPrimary': '#abcdef', 'mSurface': '#202122'}}))
                second = palette.current()
                self.assertEqual(second['colors']['mPrimary'], '#abcdef')
                self.assertNotEqual(first, second)


class LivePaletteTests(unittest.TestCase):
    def test_open_center_tracks_theme_switch_with_menu_environment(self):
        import time
        import tkinter as tk
        from tkinter import ttk
        import app as application
        from settings_home import SettingsHome

        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as tmp:
            home = Path(tmp)
            executable = home / '.local/bin/hyprbar'
            executable.parent.mkdir(parents=True)
            base = home / 'state/hyprbar/community-palettes'
            base.mkdir(parents=True)
            (base / 'First.json').write_text(json.dumps({'dark': {'mSurface': '#101112', 'mPrimary': '#123456'}}))
            (base / 'Second.json').write_text(json.dumps({'light': {'mSurface': '#fafbfc', 'mPrimary': '#abcdef'}}))

            def select(name, mode):
                executable.write_text(f'#!/bin/sh\ncase "$2" in\ncolor-scheme-get) echo "community {name}";;\ntheme-mode-get) echo {mode};;\nesac\n')
                executable.chmod(0o755)

            select('First', 'dark')
            with patch.dict(os.environ, {'HOME': str(home), 'PATH': '/usr/bin:/bin', 'XDG_STATE_HOME': str(home / 'state')}), patch.object(application.cm, 'discover', return_value=[]):
                root = tk.Tk()
                try:
                    app = application.App(root, smoke=True)
                    center = SettingsHome(app)
                    report = app.report.get('1.0', 'end-1c')

                    def wait_for(surface):
                        deadline = time.monotonic() + 8
                        while time.monotonic() < deadline:
                            root.update()
                            if root.cget('background') == surface:
                                return
                            time.sleep(.01)
                        self.fail(f'Open center did not follow theme {surface}: {app.theme_status.get()}')

                    wait_for('#101112')
                    select('Second', 'light')
                    # Do not manually refresh: exercise the existing Tk timer and worker queue.
                    wait_for('#fafbfc')
                    self.assertEqual(ttk.Style(root).lookup('TFrame', 'background'), '#fafbfc')
                    self.assertEqual(ttk.Style(root).lookup('TButton', 'focuscolor'), '#abcdef')
                    self.assertEqual(app.palette_spec['name'], 'Second')
                    self.assertEqual(app.palette_spec['mode'], 'light')
                    self.assertFalse(app.palette_spec['fallback'])
                    self.assertEqual(center.home.winfo_manager(), 'pack')
                    self.assertEqual(app.report.get('1.0', 'end-1c'), report)
                    self.assertFalse(app.applied)
                finally:
                    for job in root.tk.call('after', 'info'):
                        root.after_cancel(job)
                    root.destroy()


if __name__ == '__main__':
    unittest.main()
