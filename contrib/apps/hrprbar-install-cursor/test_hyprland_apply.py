"""Apply integration uses isolated files and a real Tk/worker queue only."""
import queue
import tempfile
import threading
import time
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import hyprland_dialog as ui
import hyprland_settings as hs


class ApplyTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk(); self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.cfg = Path(self.temp.name) / 'hyprland.lua'
        self.original = b'-- isolated apply fixture\nhl.config({})\n'
        self.cfg.write_bytes(self.original)
        self.events = []; self.queue = queue.Queue()
        self.app = SimpleNamespace(root=self.root, font_family='Liberation Sans', busy=False, smoke=False)
        def operation(fn, done):
            self.app.busy = True
            def worker():
                try: self.queue.put((done, fn(), None))
                except Exception as exc: self.queue.put((done, None, exc))
            threading.Thread(target=worker, daemon=True).start()
        self.app.operation = operation
        outer = self
        class Runtime:
            config = outer.cfg; binary = Path('/fixture/Hyprland'); instance = {'instance': 'apply-fixture'}
            safe = False
            mismatch = False
            reload_error = False
            def options(self):
                return [hs.Option({'name': 'animations:workspace_wraparound', 'current': False, 'default': True}),
                        hs.Option({'name': 'general:border_size', 'current': 1, 'min': 0, 'max': 20})]
            def readback(self, names):
                outer.events.append(('read', tuple(names)))
                return {name: ({'bool': self.safe} if name == 'misc:disable_autoreload' else
                              {'bool': not self.mismatch} if name == 'animations:workspace_wraparound' else {'int': 3}) for name in names}
            def disable_autoreload(self):
                outer.events.append('disable'); self.safe = True; self.ensure_save_safe()
            def ensure_save_safe(self):
                outer.events.append('safe')
                if not self.safe: raise ValueError('unsafe fixture')
            def reload(self):
                outer.events.append('reload')
                if self.reload_error: raise RuntimeError('fixture reload error')
        self.dialog = ui.HyprlandDialog(self.app, runtime_factory=Runtime)
        self.pump()
        self.dialog.tree.selection_set('animations:workspace_wraparound'); self.dialog.choose(); self.root.update()
        self.events.clear()

    def pump(self):
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            self.root.update()
            try:
                while True:
                    done, result, error = self.queue.get_nowait()
                    self.app.busy = False
                    done(result, error)
            except queue.Empty: pass
            if not self.dialog.busy and not self.app.busy: return
            time.sleep(.005)
        self.fail('worker queue timeout')

    def test_one_click_includes_unstaged_bool_and_verifies_runtime(self):
        d = self.dialog
        d.bool_value.set('Ativado'); d.bool_box.event_generate('<<ComboboxSelected>>'); self.root.update()
        self.assertFalse(d.staged)
        with patch.object(d, 'confirm_diff', return_value=True) as confirm:
            d.apply_button.invoke()
        self.pump()
        self.assertIn(b'["animations.workspace_wraparound"] = true', self.cfg.read_bytes())
        self.assertEqual(self.events.count('reload'), 1)
        self.assertEqual(self.events.count('disable'), 1)
        self.assertTrue(confirm.call_args.kwargs['apply'])
        self.assertTrue(d.options['animations:workspace_wraparound'].current)
        self.assertIs(d.options['animations:workspace_wraparound'].raw['current'], True)
        self.assertEqual(d.tree.item('animations:workspace_wraparound', 'values')[0], 'true')
        self.assertFalse(d.staged)
        self.assertFalse(d.pending())
        self.assertIn('verificad', d.status.get().lower())
        self.assertEqual(len(list(Path(self.temp.name).glob('*.backup-*'))), 1)
    def test_boolean_selector_is_readonly_portuguese_and_sets_encoded_values(self):
        d = self.dialog
        self.assertEqual(str(d.bool_box['state']), 'readonly')
        self.assertEqual(tuple(d.bool_box['values']), ('Ativado', 'Desativado'))
        self.assertFalse(d.value_entry.winfo_ismapped())
        for label, encoded in [('Ativado', 'true'), ('Desativado', 'false')]:
            d.bool_value.set(label); d.bool_box.event_generate('<<ComboboxSelected>>'); self.root.update()
            self.assertEqual(d.value.get(), encoded)
        self.assertEqual(self.events, [])

    def test_pending_editor_survives_selection_events_filter_and_controls(self):
        d = self.dialog
        d.value.set('true')
        self.assertTrue(d.pending())
        self.assertIn('pendente', d.status.get().lower())
        d.choose(); d.controls(True); d.controls(False); d.filter(); self.root.update()
        self.assertEqual(d.value.get(), 'true')
        d.tree.selection_set('general:border_size'); d.choose(); d.value.set('3')
        d.tree.selection_set('animations:workspace_wraparound'); d.choose(); self.root.update()
        self.assertEqual(d.value.get(), 'true')
        self.assertEqual(self.events, [])
        with patch.object(ui.messagebox, 'askyesno', return_value=False): d.load()
        self.assertEqual(d.value.get(), 'true')
        self.assertEqual(self.events, [])

    def test_invalid_nonbool_input_is_explicit_and_does_not_confirm(self):
        d = self.dialog
        d.tree.selection_set('general:border_size'); d.choose(); d.value.set('not-an-int')
        with patch.object(d, 'confirm_diff', side_effect=AssertionError('no invalid confirmation')):
            d.apply()
        self.assertIn('inválido', d.status.get())
        self.assertEqual(self.events, [])
        self.assertEqual(self.cfg.read_bytes(), self.original)
    def test_confirmation_cancel_has_no_file_or_runtime_mutations(self):
        d = self.dialog; d.value.set('true'); d.runtime.safe = True
        with patch.object(d, 'confirm_diff', return_value=False): d.apply_button.invoke()
        self.assertEqual(self.cfg.read_bytes(), self.original)
        self.assertEqual(self.events, [])
        self.assertTrue(d.runtime.safe)
        self.assertEqual(d.value.get(), 'true')
        self.assertIn('cancelada', d.status.get())

    def test_double_apply_during_confirmation_is_not_reentrant(self):
        d = self.dialog; d.value.set('true')
        def confirm(*args, **kwargs):
            d.apply()
            return False
        with patch.object(d, 'confirm_diff', side_effect=confirm) as confirmation: d.apply()
        self.assertEqual(confirmation.call_count, 1)
        self.assertFalse(d.busy)
        self.assertEqual(self.events, [])

    def test_runtime_mismatch_retains_staged_and_does_not_claim_success(self):
        d = self.dialog; d.value.set('true'); d.runtime.mismatch = True
        actual = hs.apply_changes
        with patch.object(d, 'confirm_diff', return_value=True), patch.object(hs, 'apply_changes', side_effect=lambda *args: actual(*args, verify_timeout=.02, poll_interval=.001)):
            d.apply(); self.pump()
        self.assertEqual(self.events.count('reload'), 1)
        self.assertIs(d.options['animations:workspace_wraparound'].current, False)
        self.assertEqual(d.staged, {'animations:workspace_wraparound': True})
        self.assertIn('Salvo, mas', d.status.get())
        self.assertIn('divergentes', d.status.get())
        backup = next(Path(self.temp.name).glob('*.backup-*'))
        self.assertIn(str(backup), d.status.get())
        self.assertEqual(backup.read_bytes(), self.original)

    def test_reload_error_reports_saved_and_keeps_proposal_for_retry(self):
        d = self.dialog; d.value.set('true'); d.runtime.reload_error = True
        with patch.object(d, 'confirm_diff', return_value=True): d.apply(); self.pump()
        self.assertIn('fixture reload error', d.status.get())
        self.assertIn('Salvo, mas', d.status.get())
        self.assertTrue(d.staged)
        self.assertFalse(d.options['animations:workspace_wraparound'].current)
        self.assertIn('Backup:', d.status.get())
        self.assertNotEqual(self.cfg.read_bytes(), self.original)

    def test_smoke_and_app_busy_block_before_confirmation(self):
        d = self.dialog; d.value.set('true')
        with patch.object(d, 'confirm_diff', side_effect=AssertionError('must be blocked')):
            self.app.smoke = True; d.apply()
            self.assertIn('smoke', d.status.get())
            self.app.smoke = False; self.app.busy = True; d.apply()
            self.app.busy = False; d.busy = True; d.apply(); d.busy = False
        self.assertEqual(self.events, [])
        self.assertEqual(self.cfg.read_bytes(), self.original)

    def test_double_apply_while_worker_is_pending_runs_once(self):
        d = self.dialog; d.value.set('true')
        with patch.object(d, 'confirm_diff', return_value=True) as confirmation:
            d.apply(); d.apply()
            self.assertEqual(confirmation.call_count, 1)
        self.pump()
        self.assertEqual(self.events.count('reload'), 1)

    def test_advanced_lua_is_saved_with_scalar_edits_and_warns_unverified_effects(self):
        d = self.dialog; d.value.set('true'); d.code.insert('end', '-- custom hook edit\n')
        with patch.object(d, 'confirm_diff', return_value=True) as confirm: d.apply(); self.pump()
        self.assertIn('-- custom hook edit', confirm.call_args.args[0])
        self.assertIn('animations.workspace_wraparound', confirm.call_args.args[0])
        self.assertTrue(confirm.call_args.kwargs['apply'])
        self.assertIn(b'-- custom hook edit', self.cfg.read_bytes())
        self.assertIn('não verificáveis', d.status.get())

    def test_apply_confirmation_contains_complete_diff_and_hook_warning(self):
        d = self.dialog; captured = {}
        def inspect_cancel():
            dialogs = [w for w in d.window.winfo_children() if isinstance(w, tk.Toplevel)]
            if not dialogs: self.root.after(10, inspect_cancel); return
            modal = dialogs[0]
            captured['labels'] = '\n'.join(str(w.cget('text')) for w in modal.winfo_children() if w.winfo_class() == 'TLabel')
            captured['diff'] = next(w for w in modal.winfo_children() if isinstance(w, tk.Text)).get('1.0', 'end-1c')
            captured['horizontal'] = next(w for w in modal.winfo_children() if isinstance(w, tk.Text)).cget('xscrollcommand')
            modal.destroy()
        self.root.after(30, inspect_cancel)
        self.assertFalse(d.confirm_diff('full diff\n' * 500, apply=True))
        self.assertEqual(captured['diff'], 'full diff\n' * 500)
        self.assertIn('RECARREGA', captured['labels'])
        self.assertIn('hooks', captured['labels'])
        self.assertIn('NÃO', captured['labels'])
        self.assertTrue(captured['horizontal'])
        self.assertEqual(self.events, [])
    def test_managed_scalar_edited_in_advanced_editor_is_verified_not_custom_only(self):
        d = self.dialog
        d.code.delete('1.0', 'end')
        d.code.insert('1.0', hs.managed_config(self.original, {'general:border_size': 3}).decode())
        with patch.object(d, 'confirm_diff', return_value=True): d.apply(); self.pump()
        self.assertEqual(d.options['general:border_size'].current, 3)
        self.assertEqual(d.options['general:border_size'].raw['current'], 3)
        self.assertIn('1 valores escalares verificados', d.status.get())

    def test_staged_invalid_scalar_type_does_not_reach_confirmation(self):
        d = self.dialog; d.staged['general:border_size'] = 'wrong-type'
        with patch.object(d, 'confirm_diff', side_effect=AssertionError('invalid full proposal')):
            d.apply()
        self.assertIn('inválido', d.status.get())
        self.assertEqual(self.events, [])
        self.assertEqual(self.cfg.read_bytes(), self.original)

    def test_false_boolean_selector_applies_false_without_free_text(self):
        d = self.dialog
        option = d.options['animations:workspace_wraparound']; option.current = True; option.raw['current'] = True
        d._editor_name = None; d.choose()
        original_readback = d.runtime.readback
        def readback(names):
            result = original_readback(names)
            if 'animations:workspace_wraparound' in result: result['animations:workspace_wraparound'] = {'bool': False}
            return result
        d.runtime.readback = readback
        d.bool_value.set('Desativado'); d.bool_box.event_generate('<<ComboboxSelected>>'); self.root.update()
        with patch.object(d, 'confirm_diff', return_value=True): d.apply_button.invoke(); self.pump()
        self.assertIn(b'["animations.workspace_wraparound"] = false', self.cfg.read_bytes())
        self.assertIs(option.current, False)
        self.assertFalse(d.pending())

    def test_primary_action_has_distinct_bold_style(self):
        d = self.dialog
        self.assertIn('bold', str(d.style.lookup(d.apply_button['style'], 'font')))
    def test_single_visible_configuration_action_and_no_staging_buttons(self):
        d = self.dialog
        from tkinter import ttk
        def buttons(widget):
            return [child for child in widget.winfo_children() if isinstance(child, ttk.Button)] + [button for child in widget.winfo_children() for button in buttons(child)]
        labels = [str(button['text']) for button in buttons(d.window)]
        self.assertIn('Aplicar e recarregar', labels)
        self.assertEqual(set(labels), {'Aplicar e recarregar', 'Fechar', 'Reler do compositor / arquivo', 'Voltar ao início'})

    def test_valid_drafts_are_visible_and_invalid_switched_draft_blocks_apply(self):
        d = self.dialog; d.value.set('true')
        self.assertEqual(d.tree.item('animations:workspace_wraparound', 'values')[1], 'true')
        d.tree.selection_set('general:border_size'); d.choose(); d.value.set('invalid')
        d.tree.selection_set('animations:workspace_wraparound'); d.choose()
        with patch.object(d, 'confirm_diff', side_effect=AssertionError('invalid old draft')): d.apply()
        self.assertIn('inválido', d.status.get())
        self.assertEqual(self.events, [])


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'hyprland.lua'; self.path.write_bytes(b'-- old\n')
        self.doc = hs.Document(self.path)
        self.changes = {'test:bool': True, 'test:int': 3, 'test:float': 1.25, 'test:str': 'br'}
        self.events = []; self.reads = 0
        outer = self
        class Runtime:
            safe = True
            def readback(self, names):
                outer.events.append(('read', tuple(names)))
                if names == ['misc:disable_autoreload']: return {'misc:disable_autoreload': {'bool': self.safe}}
                outer.reads += 1
                return {'test:bool': {'bool': outer.reads >= 3}, 'test:int': {'int': 3},
                        'test:float': {'float': 1.25}, 'test:str': {'str': 'br'}}
            def ensure_save_safe(self):
                if not self.safe: raise ValueError('unsafe')
            def disable_autoreload(self): outer.events.append('disable'); self.safe = True
            def reload(self): outer.events.append('reload')
        self.runtime = Runtime()

    def test_apply_polls_delayed_scalars_and_does_not_disable_already_safe_runtime(self):
        result = hs.apply_changes(self.runtime, self.doc, b'-- new\n', self.changes,
                                  verify_timeout=.1, poll_interval=.001)
        self.assertTrue(result['verified'], result)
        self.assertEqual(result['observed'], self.changes)
        self.assertEqual(self.reads, 3)
        self.assertNotIn('disable', self.events)

    def test_preserves_original_disabled_autoreload_after_reload_resets_it(self):
        def reload(): self.events.append('reload'); self.runtime.safe = False
        self.runtime.reload = reload
        self.reads = 3
        result = hs.apply_changes(self.runtime, self.doc, b'-- new\n', self.changes)
        self.assertTrue(result['verified'], result)
        self.assertTrue(self.runtime.safe)
        self.assertIn('disable', self.events)

    def test_scalar_schema_is_strict_and_never_coerces_wrong_types(self):
        cases = [(True, {'bool': True}, True), (False, {'int': 0}, False),
                 (3, {'int': 3}, 3), (1.25, {'float': 1.25}, 1.25), ('br', {'str': 'br'}, 'br')]
        for expected, raw, value in cases:
            with self.subTest(raw=raw): self.assertEqual(hs.observed_scalar(raw, expected), value)
        for expected, raw in [(False, {}), (True, {'bool': False, 'int': 1}),
                              (True, {'bool': 1}), (1, {'int': True}), (1, {'int': '1'}),
                              (1.0, {'float': '1'}), ('1', {'str': 1})]:
            with self.subTest(expected=expected, raw=raw):
                if raw == {'bool': False, 'int': 1}:
                    self.assertIs(hs.observed_scalar(raw, expected), False)
                else:
                    with self.assertRaises(ValueError): hs.observed_scalar(raw, expected)
    def test_write_failure_reports_backup_without_reloading_or_losing_original(self):
        self.reads = 3
        with patch.object(hs.os, 'replace', side_effect=OSError('fixture disk full')):
            result = hs.apply_changes(self.runtime, self.doc, b'-- new\n', self.changes)
        self.assertFalse(result['saved']); self.assertFalse(result['verified'])
        self.assertEqual(self.path.read_bytes(), b'-- old\n')
        self.assertNotIn('reload', self.events)
        backup = next(Path(self.temp.name).glob('*.backup-*'))
        self.assertEqual(result['backup'], backup)
        self.assertIn(str(backup), result['error'])

    def test_invalid_complete_lua_does_not_disable_autoreload_or_save(self):
        self.runtime.safe = False
        result = hs.apply_changes(self.runtime, self.doc, b'broken Lua!!!\n', self.changes)
        self.assertFalse(result['saved']); self.assertFalse(result['verified'])
        self.assertEqual(self.events, [])
        self.assertEqual(self.path.read_bytes(), b'-- old\n')
        self.assertFalse(list(Path(self.temp.name).glob('*.backup-*')))

    def test_unknown_autoreload_readback_does_not_mutate_runtime(self):
        self.runtime.readback = lambda names: {'misc:disable_autoreload': {}}
        result = hs.apply_changes(self.runtime, self.doc, b'-- new\n', self.changes)
        self.assertFalse(result['saved']); self.assertFalse(result['verified'])
        self.assertEqual(self.events, [])
        self.assertEqual(self.path.read_bytes(), b'-- old\n')

    def test_explicit_false_autoreload_scalar_is_not_overridden_by_preservation(self):
        self.reads = 3
        def readback(names):
            if names == ['misc:disable_autoreload']:
                return {'misc:disable_autoreload': {'bool': self.runtime.safe}}
            return {}
        self.runtime.readback = readback
        def reload(): self.events.append('reload'); self.runtime.safe = False
        self.runtime.reload = reload
        result = hs.apply_changes(self.runtime, self.doc, b'-- new\n', {'misc:disable_autoreload': False})
        self.assertTrue(result['verified'], result)
        self.assertFalse(self.runtime.safe)
        self.assertNotIn('disable', self.events)


if __name__ == '__main__': unittest.main()
