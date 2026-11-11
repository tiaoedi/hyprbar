"""Real Tk layout/palette regressions; isolated Lua, no desktop writes."""
import tempfile
import time
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from types import SimpleNamespace
import unittest

from hyprland_dialog import HyprlandDialog
import hyprland_settings as hs


class HyprlandLayoutTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        cfg = Path(self.temp.name) / 'hyprland.lua'
        cfg.write_text('-- isolated layout fixture\nhl.config({})\n')
        class Runtime:
            config = cfg
            binary = Path('/fixture/Hyprland')
            instance = {'instance': 'layout-fixture'}
            def options(self):
                return [hs.Option({'name': 'general:border_size', 'current': 1,
                                   'default': 1, 'description': 'Border width.'})]
        self.app = SimpleNamespace(root=self.root, font_family='Liberation Sans',
                                   busy=False, smoke=True, palette_spec={'colors': {
                                       'mSurface': '#191724', 'mSurfaceVariant': '#26233a',
                                       'mOnSurface': '#e0def4', 'mPrimary': '#c4a7e7',
                                       'mOnPrimary': '#191724', 'mOutline': '#6e6a86'}})
        def operation(fn, done):
            try:
                result = fn()
            except Exception as error:
                done(None, error)
            else:
                done(result, None)
        self.app.operation = operation
        self.style = ttk.Style(self.root)
        self.style.theme_use('clam')
        self.style.configure('Treeview', rowheight=64)
        self.dialog = HyprlandDialog(self.app, runtime_factory=Runtime)
        # A tiling compositor otherwise ignores the requested test dimensions.
        self.dialog.window.overrideredirect(True)
        self.dialog.window.geometry('900x850+60+60')
        self.root.update()
        self.assertEqual(self.dialog.window.winfo_width(), 900)

    def test_tree_rows_are_compact_without_changing_global_default(self):
        style = str(self.dialog.tree.cget('style')) or 'Treeview'
        self.assertLessEqual(int(self.style.lookup(style, 'rowheight')), 36)
        self.assertGreaterEqual(int(self.style.lookup(style, 'rowheight')), 28)
        self.assertEqual(int(self.style.lookup('Treeview', 'rowheight')), 64)

    def test_footer_buttons_are_fully_visible_at_900_pixels(self):
        dialog = self.dialog
        footer = dialog.apply_button.master
        buttons = [widget for row in footer.winfo_children()
                   for widget in ([row] if isinstance(row, ttk.Button) else row.winfo_children())
                   if isinstance(widget, ttk.Button)]
        self.assertEqual(len(buttons), 2)
        self.assertEqual({str(button['text']) for button in buttons}, {'Aplicar e recarregar', 'Fechar'})
        rows = set()
        for button in buttons:
            with self.subTest(button=button.cget('text')):
                self.assertTrue(button.winfo_ismapped())
                x = button.winfo_rootx() - dialog.window.winfo_rootx()
                y = button.winfo_rooty() - dialog.window.winfo_rooty()
                self.assertGreaterEqual(x, 0)
                self.assertLessEqual(x + button.winfo_width(), 900)
                self.assertGreaterEqual(button.winfo_width(), button.winfo_reqwidth())
                self.assertLessEqual(y + button.winfo_height(), dialog.window.winfo_height())
                rows.add(y)
        self.assertEqual(len(rows), 1)

    def test_safety_warning_wraps_and_option_table_scrolls_at_900_pixels(self):
        labels=[]
        def collect(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Label) and str(child.cget('text')).startswith('ATENÇÃO:'):
                    labels.append(child)
                collect(child)
        collect(self.dialog.window)
        self.assertEqual(len(labels),1)
        self.dialog.tabs.select(1)
        self.root.update()
        self.assertLessEqual(int(labels[0].cget('wraplength')), labels[0].master.winfo_width())
        self.assertTrue(self.dialog.tree.cget('xscrollcommand'), 'Every option column must remain accessible')

    def assert_palette(self):
        colors = self.app.palette_spec['colors']
        for text in (self.dialog.details, self.dialog.code):
            for option, color in [('background', 'mSurfaceVariant'),
                                  ('foreground', 'mOnSurface'),
                                  ('insertbackground', 'mOnSurface'),
                                  ('selectbackground', 'mPrimary'),
                                  ('selectforeground', 'mOnPrimary')]:
                self.assertEqual(text.cget(option), colors[color])

    def test_text_uses_current_palette(self):
        self.assert_palette()

    def test_palette_changes_are_polled_locally_and_cancelled_on_destroy(self):
        original = self.dialog.code.get('1.0', 'end-1c')
        self.app.palette_spec['colors']['mSurfaceVariant'] = '#313244'
        self.app.palette_spec['colors']['mOnSurface'] = '#cdd6f4'
        deadline = time.monotonic() + 1.5
        while time.monotonic() < deadline:
            self.root.update()
            if self.dialog.code.cget('background') == '#313244':
                break
            time.sleep(.01)
        self.assert_palette()
        self.assertEqual(self.dialog.code.get('1.0', 'end-1c'), original)
        self.assertEqual(str(self.dialog.details.cget('state')), 'disabled')
        jobs = set(self.root.tk.call('after', 'info'))
        self.assertEqual(len(jobs), 1)
        self.dialog.window.destroy()
        self.root.update()
        self.assertFalse(jobs.intersection(self.root.tk.call('after', 'info')))


if __name__ == '__main__':
    unittest.main()
