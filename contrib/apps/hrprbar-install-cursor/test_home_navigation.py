"""Real Tk return-home navigation; isolated GUI, no runtime writes."""
import os
from pathlib import Path
import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import patch

from app import App
from settings_home import SettingsHome
from hyprland_dialog import HyprlandDialog
import hyprland_settings as hs


@unittest.skipUnless(os.environ.get('DISPLAY'), 'GUI requires DISPLAY')
class ReturnHomeTests(unittest.TestCase):
    def setUp(self):
        self.temp = self.enterContext(tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')))
        self.enterContext(patch('app.cm.discover', return_value=[]))
        self.enterContext(patch('app.App.refresh_palette'))
        self.enterContext(patch('icons.discover', return_value=[]))
        self.root = tk.Tk()
        self.addCleanup(self.cleanup)
        self.app = App(self.root, smoke=True)
        self.home = SettingsHome(self.app)
        self.home.show_cursors()

    def cleanup(self):
        for job in self.root.tk.call('after', 'info'):
            self.root.after_cancel(job)
        self.root.destroy()

    def assert_home(self):
        self.root.update()
        self.assertEqual(self.home.home.winfo_manager(), 'pack')
        self.assertFalse(any(frame.winfo_manager() for frame in self.home.cursor_frames))
        self.assertFalse(self.app.applied)

    def hyprland(self):
        cfg = Path(self.temp) / 'hyprland.lua'
        cfg.write_text('-- navigation fixture\nhl.config({})\n')
        class Runtime:
            config = cfg
            binary = Path('/fixture/Hyprland')
            instance = {'instance': 'navigation-fixture'}
            def options(self):
                return [hs.Option({'name': 'general:border_size', 'current': 1, 'default': 1})]
        dialog = HyprlandDialog(self.app, runtime_factory=Runtime)
        self.app.hyprland_dialog = dialog
        deadline = time.monotonic() + 5
        while dialog.document is None and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.01)
        self.assertIsNotNone(dialog.document)
        return dialog

    def test_cursor_view_returns_to_home(self):
        self.home.home_button.invoke()
        self.assert_home()

    def test_each_module_has_visible_button_and_closes_on_return(self):
        from online_dialog import OnlineDialog
        from icon_catalog_dialog import IconCatalogDialog
        for kind in ['hyprland', 'icons', 'cursor-downloads', 'icon-downloads', 'icon-catalog']:
            with self.subTest(screen=kind):
                self.home.show_cursors()
                if kind == 'hyprland':
                    dialog = self.hyprland()
                elif kind == 'cursor-downloads':
                    self.app.open_online()
                    dialog = self.app.online_dialog
                else:
                    self.app.open_icons()
                    owner = self.app.icon_dialog
                    dialog = owner
                    if kind == 'icon-downloads':
                        dialog = OnlineDialog(self.app, icon_owner=owner)
                        owner.online_dialog = dialog
                    elif kind == 'icon-catalog':
                        dialog = IconCatalogDialog(owner)
                        owner.catalog_dialog = dialog
                self.root.update()
                def descendants(w):
                    return [w] + [child for item in w.winfo_children() for child in descendants(item)]
                visible = [w for w in descendants(self.root)
                           if (w is self.root or isinstance(w, tk.Toplevel)) and w.winfo_ismapped()]
                self.assertEqual(visible, [dialog.window], 'Only the current screen may be visible')
                self.assertTrue(hasattr(dialog, 'home_button'), kind+' has no return-home button')
                self.assertEqual(dialog.home_button.cget('text'), 'Voltar ao início')
                self.assertTrue(dialog.home_button.winfo_ismapped())
                dialog.home_button.invoke()
                self.assertFalse(dialog.window.winfo_exists())
                self.assert_home()
                self.assertFalse(any(isinstance(w, tk.Toplevel) for w in self.root.winfo_children()))

    def test_return_does_not_close_during_operation(self):
        self.app.open_icons()
        dialog = self.app.icon_dialog
        self.assertTrue(hasattr(dialog, 'home_button'), 'missing return-home button')
        self.app.busy = True
        dialog.home_button.invoke()
        self.home.home_button.invoke()
        self.assertTrue(dialog.window.winfo_exists())
        self.assertFalse(self.home.home.winfo_manager())
        self.app.busy = False
        dialog.home_button.invoke()
        self.assert_home()

    def test_normal_close_restores_only_the_previous_screen(self):
        from online_dialog import OnlineDialog
        self.app.open_icons()
        owner = self.app.icon_dialog
        dialog = OnlineDialog(self.app, icon_owner=owner)
        owner.online_dialog = dialog
        self.root.update()
        self.assertFalse(self.root.winfo_ismapped())
        self.assertFalse(owner.window.winfo_ismapped())
        self.assertTrue(dialog.window.winfo_ismapped())
        dialog.close()
        self.root.update()
        self.assertFalse(self.root.winfo_ismapped())
        self.assertTrue(owner.window.winfo_ismapped())
        owner.home_button.invoke()
        self.assert_home()
        self.assertEqual(self.app._home_screens, [])

    def test_owner_stays_open_when_nested_dialog_refuses_close(self):
        from online_dialog import OnlineDialog
        self.app.open_icons()
        owner = self.app.icon_dialog
        nested = OnlineDialog(self.app, icon_owner=owner)
        owner.online_dialog = nested
        self.root.update()
        nested.close = lambda: None
        self.app._home_screens = [
            (window, nested.close if window is nested.window else close)
            for window, close in self.app._home_screens
        ]
        nested.home_button.invoke()
        self.assertTrue(owner.window.winfo_exists())
        self.assertTrue(nested.window.winfo_exists())
        self.assertTrue(nested.window.winfo_ismapped())
        owner.close()
        self.assertTrue(owner.window.winfo_exists())
        self.assertTrue(nested.window.winfo_exists())

    def test_unsaved_hyprland_draft_requires_confirmation_and_preserves_cancel(self):
        dialog = self.hyprland()
        self.assertTrue(hasattr(dialog, 'home_button'), 'missing return-home button')
        original = dialog.document.path.read_bytes()
        dialog.code.insert('end', '\n-- unsaved draft')
        with patch('hyprland_dialog.messagebox.askyesno', return_value=False) as confirm:
            dialog.home_button.invoke()
            confirm.assert_called_once()
        self.assertTrue(dialog.window.winfo_exists())
        self.assertTrue(dialog.window.winfo_ismapped())
        self.assertFalse(self.home.home.winfo_manager())
        self.assertIn('-- unsaved draft', dialog.code.get('1.0', 'end'))
        with patch('hyprland_dialog.messagebox.askyesno', return_value=True):
            dialog.home_button.invoke()
        self.assertFalse(dialog.window.winfo_exists())
        self.assertEqual(Path(self.temp, 'hyprland.lua').read_bytes(), original)
        self.assert_home()

    def test_return_from_auxiliary_app_screen_closes_it(self):
        from types import SimpleNamespace
        self.app.show_apps([], SimpleNamespace(name='fixture'), 32)
        dialog = next(w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel))
        def buttons(widget):
            found = []
            for child in widget.winfo_children():
                if child.winfo_class() == 'TButton' and child.cget('text') == 'Voltar ao início':
                    found.append(child)
                found.extend(buttons(child))
            return found
        home_buttons = buttons(dialog)
        self.assertEqual(len(home_buttons), 1, 'auxiliary screen has no return-home button')
        home_buttons[0].invoke()
        self.assertFalse(dialog.winfo_exists())
        self.assert_home()


if __name__ == '__main__':
    unittest.main()
