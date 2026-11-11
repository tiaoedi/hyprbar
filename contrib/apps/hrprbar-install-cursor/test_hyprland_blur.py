"""Glass quick setting: real Tk, isolated document, fake compositor only."""
import unittest
from unittest.mock import patch

import hyprland_settings as hs
import test_hyprland_apply as fixtures

BLUR = 'decoration:blur:enabled'


class BlurTests(unittest.TestCase):
    # Reuse setup/queue helpers, never inherit the fixture's test methods.
    setUp = fixtures.ApplyTests.setUp
    pump = fixtures.ApplyTests.pump

    def add_blur(self, current=True):
        self.assertTrue(hasattr(self.dialog, 'blur_box'), 'Missing glass quick setting')
        option = hs.Option({'name': BLUR, 'current': current, 'default': True,
                            'description': 'enable window background blur'})
        self.dialog.options[BLUR] = option
        self.dialog.filter()
        return self.dialog

    def pick(self, label):
        d = self.dialog
        d.blur_value.set(label)
        d.blur_box.event_generate('<<ComboboxSelected>>')
        self.root.update()

    def test_quick_dropdown_stages_both_labels_without_writes_and_clears_at_current(self):
        d = self.add_blur()
        self.assertEqual(tuple(d.blur_box['values']), ('Ativado', 'Desativado'))
        self.assertEqual(str(d.blur_box['state']), 'readonly')
        self.assertEqual(d.blur_value.get(), 'Ativado')
        self.assertIn('Atual: Ativado', d.blur_status.get())
        self.pick('Desativado')
        self.assertEqual(d.drafts[BLUR], 'false')
        self.assertIn('Pendente: Desativado', d.blur_status.get())
        self.assertIn('Aplicar e recarregar', d.blur_note['text'])
        self.assertEqual(self.events, [])
        self.assertEqual(self.cfg.read_bytes(), self.original)
        self.pick('Ativado')
        self.assertNotIn(BLUR, d.drafts)
        self.assertNotIn(BLUR, d.staged)
        self.assertFalse(d.pending())
        d.options[BLUR].current = False; d.filter()
        self.pick('Ativado')
        self.assertEqual(d.drafts[BLUR], 'true')

    def test_busy_smoke_and_unloaded_controls_disable_and_ignore_events(self):
        d = self.add_blur()
        for owner, attr in [(d, 'busy'), (self.app, 'busy'), (self.app, 'smoke')]:
            with self.subTest(attr=attr, owner=type(owner).__name__):
                setattr(owner, attr, True); d.controls(False)
                self.assertEqual(str(d.blur_box['state']), 'disabled')
                self.pick('Desativado')
                self.assertNotIn(BLUR, d.drafts)
                self.assertEqual(d.blur_value.get(), 'Ativado')
                setattr(owner, attr, False); d.controls(False)
                self.assertEqual(str(d.blur_box['state']), 'readonly')
        d.controls(True)
        self.assertEqual(str(d.blur_box['state']), 'disabled')
        document = d.document; d.document = None; d.controls(False)
        self.assertEqual(str(d.blur_box['state']), 'disabled')
        self.pick('Desativado'); self.assertFalse(d.drafts)
        d.document = document
        self.assertEqual(self.events, [])

    def test_quick_change_preserves_other_drafts_filters_and_selection(self):
        d = self.add_blur()
        d.tree.selection_set('general:border_size'); d.choose(); d.value.set('3')
        d.search.set('border'); d.category.set('general')
        self.pick('Desativado')
        self.assertEqual(d.search.get(), 'border')
        self.assertEqual(d.category.get(), 'general')
        self.assertEqual(d.tree.selection(), ('general:border_size',))
        self.assertEqual(d.value.get(), '3')
        self.assertEqual(d.drafts, {'general:border_size': '3', BLUR: 'false'})
        d.search.set(''); d.category.set('Todas'); self.root.update()
        self.assertEqual(d.tree.set(BLUR, 'staged'), 'false')
        self.assertEqual(self.events, [])

    def test_explorer_and_quick_dropdown_share_draft_and_staged_values(self):
        d = self.add_blur()
        d.tree.selection_set(BLUR); d.choose()
        d.bool_value.set('Desativado'); d.bool_box.event_generate('<<ComboboxSelected>>'); self.root.update()
        self.assertEqual(d.blur_value.get(), 'Desativado')
        d.stage()
        self.assertEqual(d.staged[BLUR], False)
        self.pick('Ativado')
        self.assertEqual(d.value.get(), 'true')
        self.assertEqual(d.bool_value.get(), 'Ativado')
        self.assertNotIn(BLUR, d.staged)
        self.assertNotIn(BLUR, d.drafts)
        self.pick('Desativado')
        self.assertEqual(d.value.get(), 'false')
        self.assertEqual(d.bool_value.get(), 'Desativado')
        d.unstage()
        self.assertEqual(d.blur_value.get(), 'Ativado')

    def test_missing_nonboolean_or_readonly_schema_is_unavailable(self):
        d = self.dialog
        self.assertEqual(str(d.blur_box['state']), 'disabled')
        self.assertIn('Indisponível', d.blur_status.get())
        for value in (1, 'true', None, True):
            with self.subTest(value=value):
                option = hs.Option({'name': BLUR, 'current': value})
                if value is True: option.editable = False
                d.options[BLUR] = option; d.filter()
                self.assertEqual(str(d.blur_box['state']), 'disabled')
                self.assertIn('Indisponível', d.blur_status.get())
                self.pick('Desativado'); self.assertFalse(d.drafts)
        self.assertEqual(self.events, [])

    def test_load_is_readonly_and_does_not_create_pending_edits(self):
        d = self.add_blur(False)
        options = list(d.options.values())
        d.runtime.options = lambda: options
        d.runtime_factory = lambda: d.runtime
        self.pick('Ativado')
        with patch.object(fixtures.ui.messagebox, 'askyesno', return_value=True): d.load()
        self.assertEqual(str(d.blur_box['state']), 'disabled')
        self.pick('Desativado')
        self.pump()
        self.assertEqual(d.blur_value.get(), 'Desativado')
        self.assertFalse(d.pending())
        self.assertEqual(self.events, [])
        self.assertEqual(self.cfg.read_bytes(), self.original)

    def test_cancel_quick_apply_keeps_pending_without_file_or_runtime_changes(self):
        d = self.add_blur(); self.pick('Desativado')
        with patch.object(d, 'confirm_diff', return_value=False): d.apply_button.invoke()
        self.pump()
        self.assertEqual(d.blur_value.get(), 'Desativado')
        self.assertEqual(d.drafts[BLUR], 'false')
        self.assertIn('cancelada', d.status.get())
        self.assertEqual(self.cfg.read_bytes(), self.original)
        self.assertEqual(self.events, [])

    def blur_readback(self, observed):
        d = self.dialog
        original = d.runtime.readback
        def readback(names):
            result = original(names)
            if BLUR in names: result[BLUR] = {'bool': observed}
            return result
        d.runtime.readback = readback

    def test_verified_apply_both_values_preserves_other_options_and_syncs(self):
        d = self.add_blur()
        for initial, requested in ((True, False), (False, True)):
            with self.subTest(requested=requested):
                d.options[BLUR].current = initial
                d.tree.selection_set('general:border_size'); d.choose(); d.value.set('3')
                self.pick('Ativado' if requested else 'Desativado')
                self.blur_readback(requested)
                with patch.object(d, 'confirm_diff', return_value=True): d.apply_button.invoke(); self.pump()
                encoded = b'true' if requested else b'false'
                self.assertIn(b'["decoration.blur.enabled"] = ' + encoded, self.cfg.read_bytes())
                self.assertIn(b'["general.border_size"] = 3', self.cfg.read_bytes())
                self.assertIs(d.options[BLUR].current, requested)
                self.assertEqual(d.blur_value.get(), 'Ativado' if requested else 'Desativado')
                self.assertNotIn('Pendente', d.blur_status.get())
                self.assertFalse(d.pending())
                self.assertIn('verificados', d.status.get())
        self.assertEqual(self.events.count('reload'), 2)

    def test_divergent_readback_retains_requested_vs_current_without_success(self):
        d = self.add_blur(); self.pick('Desativado'); self.blur_readback(True)
        actual = hs.apply_changes
        with patch.object(d, 'confirm_diff', return_value=True), patch.object(hs, 'apply_changes', side_effect=lambda *args: actual(*args, verify_timeout=.02, poll_interval=.001)):
            d.apply_button.invoke(); self.pump()
        self.assertIs(d.options[BLUR].current, True)
        self.assertEqual(d.blur_value.get(), 'Desativado')
        self.assertIn('Atual: Ativado', d.blur_status.get())
        self.assertIn('Pendente: Desativado', d.blur_status.get())
        self.assertIn('NÃO confirmada', d.status.get())
        self.assertNotIn('escalares verificados', d.status.get())
        self.assertTrue(d.pending())

    def test_quick_row_and_apply_are_visible_at_exact_minimum_size(self):
        d = self.add_blur(); self.pick('Desativado')
        d.window.withdraw()
        d.window.overrideredirect(True)
        d.window.geometry('900x650+60+60'); d.window.deiconify(); self.root.update()
        self.assertEqual((d.window.winfo_width(), d.window.winfo_height()), (900, 650))
        for widget in (d.blur_box.master, d.blur_box, d.blur_note, d.apply_button):
            with self.subTest(widget=widget):
                self.assertTrue(widget.winfo_ismapped())
                x = widget.winfo_rootx() - d.window.winfo_rootx()
                y = widget.winfo_rooty() - d.window.winfo_rooty()
                self.assertGreaterEqual(x, 0); self.assertGreaterEqual(y, 0)
                self.assertLessEqual(x + widget.winfo_width(), 900)
                self.assertLessEqual(y + widget.winfo_height(), 650)
                self.assertGreaterEqual(widget.winfo_width(), widget.winfo_reqwidth())
        self.assertLess(d.blur_box.winfo_rooty(), d.category_box.winfo_rooty())


if __name__ == '__main__': unittest.main()
