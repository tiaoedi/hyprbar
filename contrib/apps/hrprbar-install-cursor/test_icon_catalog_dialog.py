"""Curated icon catalog: real Tk queue, isolated homes, no desktop mutations."""
from __future__ import annotations
import importlib
import importlib.util
import os
from pathlib import Path
import socket
import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('DISPLAY'), 'GUI requires DISPLAY')
class IconCatalogGui(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.enterContext(patch.dict(os.environ, {
            'HOME': str(self.base/'home'), 'XDG_DATA_HOME': str(self.base/'data'),
            'XDG_CONFIG_HOME': str(self.base/'config'), 'XDG_STATE_HOME': str(self.base/'state'),
            'XDG_CACHE_HOME': str(self.base/'cache'), 'XDG_DATA_DIRS': str(self.base/'empty')}))
        import app
        self.enterContext(patch('app.cm.discover', return_value=[]))
        self.enterContext(patch('app.App.refresh_palette'))
        self.cursor_apply = self.enterContext(patch('app.settings.apply', side_effect=AssertionError('cursor apply forbidden')))
        self.icon_apply = self.enterContext(patch('icons.apply', side_effect=AssertionError('icon apply forbidden')))
        self.browser = self.enterContext(patch('webbrowser.open', return_value=True))
        self.network = self.enterContext(patch.object(socket, 'create_connection', side_effect=AssertionError('network forbidden')))
        self.root = tk.Tk(); self.root.withdraw()
        self.addCleanup(self.cleanup_root)
        self.app = app.App(self.root)
        self.pump(lambda: self.app.status.get().startswith('0 temas'))

    def cleanup_root(self):
        for identifier in self.root.tk.call('after', 'info'):
            self.root.after_cancel(identifier)
        self.root.destroy()

    def pump(self, predicate):
        deadline = time.monotonic()+8
        while time.monotonic() < deadline:
            self.root.update()
            if predicate(): return
            time.sleep(.01)
        self.fail('Tk worker queue timed out: '+self.app.status.get())

    def open_dialog(self):
        self.assertIsNotNone(importlib.util.find_spec('icon_catalog_dialog'), 'curated icon catalog UI missing')
        module = importlib.import_module('icon_catalog_dialog')
        self.catalog = importlib.import_module('icon_catalog')
        self.app.open_icons(); self.owner = self.app.icon_dialog
        self.pump(lambda: self.owner.status.get() != 'Lendo temas de ícones instalados…')
        self.dialog = module.IconCatalogDialog(self.owner)
        self.owner.catalog_dialog = self.dialog
        return self.dialog

    def select(self, key):
        self.dialog.tree.selection_set(key)
        self.root.update()

    def test_open_lists_six_sources_and_filters_without_side_effects(self):
        dialog = self.open_dialog()
        self.assertEqual(len(dialog.tree.get_children()), 6)
        self.assertEqual(set(dialog.tree.get_children()), {s.key for s in self.catalog.SOURCES})
        self.assertEqual(tuple(dialog.tree['columns']), ('name', 'author', 'status'))
        self.assertEqual(dialog.install_button.cget('text'), 'Baixar e instalar')
        self.assertEqual(dialog.archive_button.cget('text'), 'Instalar arquivo…')
        self.assertEqual(dialog.page_button.cget('text'), 'Abrir página do tema ↗')
        self.assertTrue(dialog.install_button.instate(['disabled']))
        for source in self.catalog.SOURCES:
            self.select(source.key)
            for value in (source.name, source.author, source.page, source.license, source.reason):
                self.assertIn(value, dialog.detail.get())
            self.assertEqual(dialog.install_button.instate(['disabled']), source.package is None)
        dialog.search.set('NEOLINE'); self.root.update()
        self.assertEqual(dialog.tree.get_children(), ('neoline',))
        dialog.search.set('not-a-theme'); self.root.update()
        self.assertEqual(dialog.tree.get_children(), ())
        self.assertTrue(dialog.install_button.instate(['disabled']))
        self.browser.assert_not_called(); self.network.assert_not_called()
        self.icon_apply.assert_not_called(); self.cursor_apply.assert_not_called()
        dialog.close()
        self.assertIsNone(self.owner.catalog_dialog)

    def test_page_and_manual_archive_are_explicit_and_guarded(self):
        dialog = self.open_dialog()
        self.assertTrue(hasattr(dialog, 'controls'), 'catalog busy/smoke controls missing')
        self.select('neoline')
        source = next(s for s in self.catalog.SOURCES if s.key == 'neoline')
        with patch.object(self.owner, 'pick_install') as pick:
            for busy, smoke in ((True, False), (False, True)):
                self.app.busy, self.app.smoke = busy, smoke
                dialog.controls(busy)
                for button in (dialog.page_button, dialog.archive_button, dialog.install_button):
                    self.assertTrue(button.instate(['disabled']))
                    button.invoke()
                dialog.open_page(); dialog.install_archive()
                self.browser.assert_not_called(); pick.assert_not_called()
            self.app.busy = self.app.smoke = False
            dialog.controls(False)
            dialog.page_button.invoke()
            self.browser.assert_called_once_with(source.page)
            dialog.archive_button.invoke(); pick.assert_called_once_with(False)
        self.browser.return_value = False
        dialog.open_page()
        self.assertIn(source.page, dialog.status.get())
        self.browser.side_effect = OSError('browser unavailable')
        dialog.open_page()
        self.assertIn('browser unavailable', dialog.status.get())
        self.app.busy = True
        dialog.close()
        self.assertTrue(dialog.window.winfo_exists())
        self.assertIn('aguarde', dialog.status.get())
        self.app.busy = False
        dialog.close(); self.assertIsNone(self.owner.catalog_dialog)
        self.network.assert_not_called()

    def test_confirmed_collection_install_uses_real_worker_queue_without_apply(self):
        import threading
        import icons
        from PIL import Image
        dialog = self.open_dialog()
        self.assertTrue(hasattr(dialog, 'install_selected'), 'confirmed catalog installation missing')
        self.select('neoline')
        source = next(s for s in self.catalog.SOURCES if s.key == 'neoline')
        package = source.package
        for value in (package.repo, package.commit, package.name, str(package.size), package.sha256):
            self.assertIn(value, dialog.detail.get())
        incoming = self.base/'incoming'
        for name in ('NeoLine', 'NeoLine-White', 'NeoLine-Yellow'):
            root = incoming/name
            (root/'32x32/apps').mkdir(parents=True)
            (root/'index.theme').write_text('[Icon Theme]\nName='+name+'\nDirectories=32x32/apps\n\n[32x32/apps]\nSize=32\nType=Fixed\nContext=Applications\n')
            Image.new('RGBA', (32, 32), '#123456').save(root/'32x32/apps/demo.png')
        gate = threading.Event(); self.addCleanup(gate.set)
        worker_threads = []
        def install(selected, destination):
            worker_threads.append(threading.get_ident())
            gate.wait(4)
            self.assertEqual(selected, source)
            return icons.install(incoming, destination)
        with patch('icon_catalog.install_source', side_effect=install) as download, \
             patch('icon_catalog_dialog.messagebox.askyesno', return_value=False) as confirm:
            dialog.install_selected(); download.assert_not_called()
            prompt = confirm.call_args.args[1]
            for value in (source.name, package.url, package.sha256, str(self.owner.destination()), 'Nada será aplicado'):
                self.assertIn(value, prompt)
            confirm.return_value = True
            dialog.install_button.invoke()
            self.assertTrue(self.app.busy)
            self.assertTrue(dialog.install_button.instate(['disabled']))
            self.assertTrue(dialog.archive_button.instate(['disabled']))
            dialog.close(); self.assertTrue(dialog.window.winfo_exists())
            self.select(next(s.key for s in self.catalog.SOURCES if s.package is None))
            gate.set()
            self.pump(lambda: not self.app.busy and self.owner.catalog_dialog is None and len(self.owner.themes) == 3)
            download.assert_called_once_with(source, self.owner.destination())
        self.assertNotEqual(worker_threads, [threading.get_ident()])
        self.assertIsNone(self.owner.selected)
        self.assertEqual(self.owner.tree.selection(), ())
        self.assertIn('Nada foi aplicado', self.owner.status.get())
        for name in ('NeoLine', 'NeoLine-White', 'NeoLine-Yellow'):
            self.assertTrue((self.owner.destination()/name/'index.theme').is_file())
        self.assertFalse((self.base/'config/gtk-3.0/settings.ini').exists())
        self.icon_apply.assert_not_called(); self.cursor_apply.assert_not_called()
        self.browser.assert_not_called(); self.network.assert_not_called()

    def test_details_and_actions_fit_minimum_window_for_every_source(self):
        dialog = self.open_dialog()
        dialog.window.overrideredirect(True)
        dialog.window.geometry('900x680+0+0')
        for source in self.catalog.SOURCES:
            with self.subTest(source=source.key):
                self.select(source.key)
                dialog.window.update_idletasks()
                self.assertEqual(dialog.window.winfo_width(), 900)
                for widget in (dialog.detail_label, dialog.status_label, dialog.page_button,
                               dialog.archive_button, dialog.install_button, dialog.tree):
                    x = widget.winfo_rootx()-dialog.window.winfo_rootx()
                    y = widget.winfo_rooty()-dialog.window.winfo_rooty()
                    self.assertGreater(widget.winfo_width(), 1)
                    self.assertGreater(widget.winfo_height(), 1)
                    self.assertLessEqual(x+widget.winfo_width(), 900)
                    self.assertLessEqual(y+widget.winfo_height(), 680)
                self.assertGreaterEqual(dialog.detail_label.winfo_height(), dialog.detail_label.winfo_reqheight())
                self.assertGreaterEqual(dialog.tree.winfo_height(), 160)
        self.browser.assert_not_called()

    def test_install_failure_stays_open_and_reenables_safe_actions(self):
        dialog = self.open_dialog()
        self.select('neoline')
        with patch('icon_catalog.install_source', side_effect=ValueError('SHA256 divergente')) as download, \
             patch('icon_catalog_dialog.messagebox.askyesno', return_value=True) as confirm:
            for busy, smoke in ((True, False), (False, True)):
                self.app.busy, self.app.smoke = busy, smoke
                dialog.controls(busy); dialog.install_selected()
                download.assert_not_called(); confirm.assert_not_called()
            self.app.busy = self.app.smoke = False
            dialog.controls(False)
            for source in self.catalog.SOURCES:
                if source.package is None:
                    self.select(source.key); dialog.install_selected()
            dialog.tree.selection_remove(*dialog.tree.selection())
            dialog.select_source(); dialog.install_selected()
            download.assert_not_called(); confirm.assert_not_called()
            self.select('neoline'); dialog.install_selected()
            self.pump(lambda: not self.app.busy and 'SHA256 divergente' in dialog.status.get())
            self.assertTrue(dialog.window.winfo_exists())
            self.assertIs(self.owner.catalog_dialog, dialog)
            self.assertTrue(dialog.install_button.instate(['!disabled']))
            self.assertTrue(dialog.archive_button.instate(['!disabled']))
            self.assertTrue(dialog.page_button.instate(['!disabled']))
            self.assertIn('Instalação recusada', dialog.status.get())
            self.assertFalse(self.owner.destination().exists())
        self.icon_apply.assert_not_called(); self.cursor_apply.assert_not_called()
        self.browser.assert_not_called(); self.network.assert_not_called()


if __name__ == '__main__':
    unittest.main()
