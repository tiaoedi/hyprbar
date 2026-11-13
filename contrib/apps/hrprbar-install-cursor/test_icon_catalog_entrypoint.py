"""Catalog entrypoint integration; no network or desktop writes."""
import os
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


@unittest.skipUnless(os.environ.get('DISPLAY'), 'GUI requires DISPLAY')
class CatalogEntrypointTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from app import App
        temporary = self.enterContext(tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')))
        base = Path(temporary)
        self.enterContext(patch.dict(os.environ, {
            'HOME': str(base/'home'), 'XDG_DATA_HOME': str(base/'data'),
            'XDG_CONFIG_HOME': str(base/'config'), 'XDG_DATA_DIRS': str(base/'empty'),
        }))
        self.enterContext(patch('app.cm.discover', return_value=[]))
        self.enterContext(patch('app.App.refresh_palette'))
        self.enterContext(patch('icons.discover', return_value=[]))
        self.root = tk.Tk(); self.root.withdraw()
        self.addCleanup(self.cleanup)
        self.app = App(self.root)
        self.app.open_icons()
        self.owner = self.app.icon_dialog
        deadline = time.monotonic()+5
        while time.monotonic() < deadline:
            self.root.update()
            if self.owner.status.get().startswith('0 temas'): break
            time.sleep(.01)
        else: self.fail('Icon discovery did not finish')

    def cleanup(self):
        for identifier in self.root.tk.call('after', 'info'):
            self.root.after_cancel(identifier)
        self.root.destroy()

    def test_catalog_button_routes_to_one_dialog_and_blocks_smoke_busy(self):
        self.assertTrue(hasattr(self.owner, 'catalog_button'), 'curated catalog entry missing')
        dialog = Mock()
        dialog.window.winfo_exists.return_value = True
        factory = Mock(return_value=dialog)
        module = types.SimpleNamespace(IconCatalogDialog=factory)
        with patch.dict('sys.modules', {'icon_catalog_dialog': module}):
            self.app.busy = True
            self.owner.open_catalog()
            factory.assert_not_called()
            self.app.busy = False; self.app.smoke = True
            self.owner.open_catalog()
            factory.assert_not_called()
            self.app.smoke = False
            self.owner.catalog_button.invoke()
            factory.assert_called_once_with(self.owner)
            self.assertIs(self.owner.catalog_dialog, dialog)
            self.owner.open_catalog()
            factory.assert_called_once()
            dialog.window.lift.assert_called_once()
    def test_catalog_participates_in_busy_controls_and_parent_close(self):
        dialog = Mock()
        dialog.window.winfo_exists.return_value = True
        self.owner.catalog_dialog = dialog
        self.owner.controls(True)
        self.assertTrue(self.owner.catalog_button.instate(['disabled']))
        dialog.controls.assert_called_with(True)
        self.owner.controls(False)
        self.assertTrue(self.owner.catalog_button.instate(['!disabled']))
        dialog.controls.assert_called_with(False)
        self.app.busy = True
        self.owner.close()
        dialog.close.assert_not_called()
        self.app.busy = False
        dialog.close.side_effect = lambda: setattr(dialog.window.winfo_exists, 'return_value', False)
        self.owner.close()
        dialog.close.assert_called_once()
        self.assertIsNone(self.app.icon_dialog)


if __name__ == '__main__':
    unittest.main()
