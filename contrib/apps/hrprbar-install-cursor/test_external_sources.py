"""External catalog links remain explicit, neutral and separate from installers."""
from __future__ import annotations

import os
import socket
import tkinter as tk
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from online_dialog import OnlineDialog


GNOME_LOOK_URL = 'https://www.gnome-look.org/browse?cat=132&ord=latest'


@unittest.skipUnless(os.environ.get('DISPLAY'), 'GUI requires DISPLAY')
class ExternalSources(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.app = SimpleNamespace(root=self.root, font_family='Liberation Sans',
                                   busy=False, smoke=False, operation=Mock())
        self.browser = self.enterContext(patch('online_dialog.webbrowser.open', return_value=True))
        self.catalog = self.enterContext(patch('online.catalog'))
        self.latest = self.enterContext(patch('online.latest'))
        self.download = self.enterContext(patch('online.install_asset'))
        self.network = self.enterContext(patch.object(socket, 'create_connection', side_effect=AssertionError('network forbidden')))

    def assert_no_download(self):
        self.app.operation.assert_not_called()
        self.catalog.assert_not_called()
        self.latest.assert_not_called()
        self.download.assert_not_called()
        self.network.assert_not_called()

    def test_exact_neutral_link_is_explicit_in_both_catalog_modes(self):
        for owner in (None, SimpleNamespace(online_dialog=None)):
            with self.subTest(icon_catalog=owner is not None):
                dialog = OnlineDialog(self.app, icon_owner=owner)
                self.browser.assert_not_called()
                self.assert_no_download()
                self.assertTrue(hasattr(dialog, 'gnome_look_button'), 'GNOME-Look external source missing')
                self.assertEqual(dialog.gnome_look_button.cget('text'), 'GNOME-Look — catálogo externo ↗')
                self.assertEqual(str(dialog.install_button.cget('state')), 'disabled')
                dialog.gnome_look_button.invoke()
                self.browser.assert_called_once_with(GNOME_LOOK_URL)
                self.assertEqual(dialog.assets, [])
                dialog.install_selected()
                self.assert_no_download()
                self.browser.reset_mock()
                dialog.window.destroy()

    def test_all_external_buttons_follow_busy_and_smoke_guards(self):
        dialog = OnlineDialog(self.app)
        buttons = (dialog.flaticon_button, dialog.custom_cursor_button, dialog.gnome_look_button)
        for busy, smoke in ((True, False), (False, True), (False, False)):
            with self.subTest(busy=busy, smoke=smoke):
                self.app.busy, self.app.smoke = busy, smoke
                dialog.controls(busy)
                for button in buttons:
                    self.assertEqual(button.instate(['disabled']), busy or smoke)
                    button.invoke()
                if busy or smoke:
                    self.browser.assert_not_called()
                    # The callback guard must also hold independently of widget state.
                    dialog.open_external(GNOME_LOOK_URL)
                    self.browser.assert_not_called()
                else:
                    self.assertEqual([call.args[0] for call in self.browser.call_args_list], [
                        'https://www.flaticon.com/br/icones-gratis/cursor',
                        'https://custom-cursor.com/es/top-downloaded-cursors',
                        GNOME_LOOK_URL,
                    ])
                self.assert_no_download()

    def test_external_warning_and_extra_row_fit_minimum_width(self):
        from tkinter import ttk
        dialog = OnlineDialog(self.app)
        dialog.window.geometry('900x680')
        dialog.window.update_idletasks()
        self.assertNotEqual(dialog.gnome_look_button.master, dialog.flaticon_button.master)
        for button in (dialog.flaticon_button, dialog.custom_cursor_button, dialog.gnome_look_button):
            self.assertLessEqual(button.winfo_x() + button.winfo_reqwidth(), button.master.winfo_width())
        def labels(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Label):
                    yield child.cget('text')
                yield from labels(child)
        warning = next(text for text in labels(dialog.window) if 'GNOME-Look:' in text)
        for notice in ('somente ao clicar', 'arquivo de tema compatível com Linux',
                       'ícones ou cursores', 'sem download ou instalação automática'):
            self.assertIn(notice, warning)
        self.browser.assert_not_called()
        self.assert_no_download()

    def test_browser_failure_reports_exact_original_url_without_download(self):
        dialog = OnlineDialog(self.app)
        self.browser.return_value = False
        dialog.gnome_look_button.invoke()
        self.browser.assert_called_once_with(GNOME_LOOK_URL)
        self.assertIn(GNOME_LOOK_URL, dialog.status.get())
        self.assert_no_download()


if __name__ == '__main__':
    unittest.main()
