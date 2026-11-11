"""Test the configuration-center entrypoint without desktop writes."""
import os
import tkinter as tk
import unittest
from unittest.mock import Mock


@unittest.skipUnless(os.environ.get('DISPLAY'), 'GUI requires DISPLAY')
class HomeTests(unittest.TestCase):
    def test_default_home_routes_modules_and_preserves_cursor_view(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec('settings_home'), 'Configuration center entrypoint is missing')
        from settings_home import SettingsHome
        root = tk.Tk(); root.withdraw()
        self.addCleanup(root.destroy)
        cursor = tk.Frame(root); cursor.pack()
        app = Mock(root=root, busy=False, smoke=True)
        home = SettingsHome(app)
        root.update_idletasks()
        self.assertTrue(home.home.winfo_manager())
        self.assertFalse(cursor.winfo_manager())
        home.hyprland_button.invoke(); app.open_hyprland.assert_called_once()
        home.icons_button.invoke(); app.open_icons.assert_called_once()
        home.cursor_button.invoke()
        self.assertTrue(cursor.winfo_manager())
        self.assertFalse(home.home.winfo_manager())
        home.home_button.invoke()
        self.assertFalse(cursor.winfo_manager())
        self.assertTrue(home.home.winfo_manager())
        self.assertEqual(root.title(), 'hrprbar-config — Central de configurações')
        app.operation.assert_not_called()

    def test_navigation_is_ignored_during_writes(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec('settings_home'), 'Configuration center entrypoint is missing')
        from settings_home import SettingsHome
        root=tk.Tk(); root.withdraw(); self.addCleanup(root.destroy)
        cursor=tk.Frame(root); cursor.pack()
        app=Mock(root=root,busy=True,smoke=True)
        home=SettingsHome(app)
        home.cursor_button.invoke()
        self.assertFalse(cursor.winfo_manager())
        home.hyprland_button.invoke(); home.icons_button.invoke()
        app.open_hyprland.assert_not_called(); app.open_icons.assert_not_called()
