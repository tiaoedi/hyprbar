"""Glass opacity regressions; compositor access is always fake."""
import unittest
import json
from unittest.mock import patch
import hyprland_settings as hs
import test_hyprland_apply as fixtures

BLUR = 'decoration:blur:enabled'
ACTIVE = 'decoration:active_opacity'
INACTIVE = 'decoration:inactive_opacity'
FULLSCREEN = 'decoration:fullscreen_opacity'


class GlassTests(unittest.TestCase):
    setUp = fixtures.ApplyTests.setUp
    pump = fixtures.ApplyTests.pump

    def glass(self, blur=True, active=1.0, inactive=1.0):
        d = self.dialog
        for name, value in ((BLUR, blur), (ACTIVE, active), (INACTIVE, inactive), (FULLSCREEN, .75)):
            d.options[name] = hs.Option({'name': name, 'current': value, 'default': value,
                                         'min': 0, 'max': 1})
        d.filter()
        return d

    def pick(self, label):
        self.dialog.blur_value.set(label)
        self.dialog.blur_box.event_generate('<<ComboboxSelected>>')
        self.root.update()

    def test_atomic_schema_availability_and_generic_explorer(self):
        d = self.glass()
        for name in (BLUR, ACTIVE, INACTIVE):
            original = d.options[name]
            for kind in (('missing', 'readonly', 'wrong') if name == BLUR else
                         ('missing', 'readonly', 'wrong', 'range')):
                with self.subTest(name=name, kind=kind):
                    option = hs.Option(dict(original.raw))
                    if kind == 'missing': d.options.pop(name)
                    else:
                        if kind == 'readonly': option.editable = False
                        if kind == 'wrong': option.current = '1'
                        if kind == 'range': option.raw['min'] = .95
                        d.options[name] = option
                    d.filter()
                    self.assertEqual(str(d.blur_box['state']), 'disabled')
                    self.assertIn('Indisponível', d.blur_status.get())
                    self.assertIn(name, d.blur_status.get())
                    self.pick('Ativado')
                    self.assertFalse(d.pending())
                    d.tree.selection_set('general:border_size'); d.choose(); d.value.set('3')
                    self.assertEqual(d.drafts['general:border_size'], '3')
                    d.unstage()
                    d.options[name] = original
        self.assertEqual(self.events, [])

    def test_composite_state_and_pending_show_raw_values_and_visible_note(self):
        d = self.glass()
        self.assertEqual(d.blur_value.get(), 'Desativado')
        self.assertIn('Atual: Desativado', d.blur_status.get())
        self.assertIn('blur=true', d.blur_status.get())
        self.assertIn('ativa=1.0', d.blur_status.get())
        self.assertIn('inativa=1.0', d.blur_status.get())
        self.pick('Ativado')
        self.assertIn('Pendente: Ativado', d.blur_status.get())
        self.assertIn('ativa=0.9', d.blur_status.get())
        self.assertIn('inativa=0.9', d.blur_status.get())
        note = d.blur_note['text']
        for text in ('90%', '100%', 'texto', 'Aplicar e recarregar'):
            self.assertIn(text, note)
        d.tree.selection_set(INACTIVE); d.choose(); d.value.set('1.0')
        self.assertEqual(d.blur_value.get(), 'Desativado')
        self.assertIn('inativa=1.0', d.blur_status.get())
        d.value.set('invalid')
        self.assertIn('inválido', d.blur_status.get())

    def test_off_with_blur_already_false_stages_both_opacities(self):
        d = self.glass(False, .8, .7)
        self.pick('Desativado')
        self.assertEqual(d.drafts, {BLUR: 'false', ACTIVE: '1.0', INACTIVE: '1.0'})
        self.assertEqual(self.events, [])

    def test_preset_verifies_all_three_even_when_blur_already_matches(self):
        d = self.glass()
        self.pick('Ativado')
        self.assertEqual(d.drafts.get(BLUR), 'true')
        observed = {BLUR: {'bool': True}, ACTIVE: {'float': .9}, INACTIVE: {'float': .9}}
        original = d.runtime.readback
        def readback(names):
            result = original(names)
            result.update({name: observed[name] for name in names if name in observed})
            return result
        d.runtime.readback = readback
        with patch.object(d, 'confirm_diff', return_value=True) as confirm:
            d.apply_button.invoke(); self.pump()
        self.assertTrue(confirm.call_args.kwargs['apply'])
        self.assertIn(('read', (BLUR, ACTIVE, INACTIVE)), self.events)
        for name, value in ((BLUR, True), (ACTIVE, .9), (INACTIVE, .9)):
            self.assertEqual(d.options[name].current, value)
            self.assertEqual(d.options[name].raw['current'], value)
        self.assertFalse(d.pending())
        self.assertEqual(d.options[FULLSCREEN].current, .75)
        for line in (b'["decoration.blur.enabled"] = true', b'["decoration.active_opacity"] = 0.9',
                     b'["decoration.inactive_opacity"] = 0.9'):
            self.assertIn(line, self.cfg.read_bytes())
        self.assertNotIn(b'fullscreen', self.cfg.read_bytes())

    def test_divergent_opacity_readback_retains_all_pending_and_metadata(self):
        d = self.glass(False, 1, 1)
        self.pick('Ativado')
        original = d.runtime.readback
        def readback(names):
            result = original(names)
            for name, raw in ((BLUR, {'bool': True}), (ACTIVE, {'float': .9}),
                              (INACTIVE, {'float': 1.0})):
                if name in names: result[name] = raw
            return result
        d.runtime.readback = readback
        actual = hs.apply_changes
        with patch.object(d, 'confirm_diff', return_value=True), patch.object(
                hs, 'apply_changes', side_effect=lambda *args: actual(*args, verify_timeout=.02, poll_interval=.001)):
            d.apply_button.invoke(); self.pump()
        self.assertEqual(d.staged, {BLUR: True, ACTIVE: .9, INACTIVE: .9})
        self.assertIs(d.options[BLUR].current, False)
        for name in (ACTIVE, INACTIVE):
            self.assertEqual(d.options[name].current, 1.0)
            self.assertEqual(d.options[name].raw['current'], 1.0)
        self.assertIn('NÃO confirmada', d.status.get())
        self.assertNotIn('escalares verificados', d.status.get())
        self.assertIn(INACTIVE, d.status.get())
        self.assertIn('Atual: Desativado', d.blur_status.get())
        self.assertIn('Pendente: Ativado', d.blur_status.get())
        self.assertTrue(d.pending())

    def test_explorer_edits_each_opacity_and_quick_change_sync_selected_editor(self):
        d = self.glass(True, .9, .9)
        for name in (ACTIVE, INACTIVE):
            d.tree.selection_set(name); d.choose(); d.value.set('1.0')
            self.assertEqual(d.blur_value.get(), 'Desativado')
            d.stage()
            self.assertEqual(d.staged[name], 1.0)
            self.pick('Ativado')
            self.assertEqual(d.value.get(), '0.9')
            self.assertNotIn(name, d.staged)
            self.pick('Desativado')
            self.assertEqual(d.value.get(), '1.0')
            self.pick('Ativado')
        self.assertFalse(d.pending())
        self.assertEqual(self.events, [])

    def test_on_with_blur_already_true_stages_transparency_without_mutating(self):
        d = self.glass()
        self.pick('Ativado')
        self.assertEqual(d.drafts.get(ACTIVE), '0.9')
        self.assertEqual(d.drafts.get(INACTIVE), '0.9')
        self.assertNotIn(FULLSCREEN, d.drafts)
        self.assertTrue(d.pending())
        self.assertEqual(d.options[ACTIVE].current, 1.0)
        self.assertEqual(self.events, [])
        self.assertEqual(self.cfg.read_bytes(), self.original)


class OpacitySchemaTests(unittest.TestCase):
    def test_captured_integer_description_has_float_semantics_and_readback(self):
        runtime = hs.Runtime.__new__(hs.Runtime)
        captured = [{'name': name, 'current': 1, 'default': 1, 'min': 0, 'max': 1}
                    for name in (ACTIVE, INACTIVE, FULLSCREEN)]
        def command(*args):
            self.assertEqual(args, ('descriptions', '-j'))
            return json.dumps(captured)
        runtime.command = command
        for option in runtime.options():
            name = option.name
            with self.subTest(name=name):
                self.assertIs(type(option.current), float)
                self.assertIs(type(option.raw['current']), float)
                self.assertEqual(option.parse('0.9'), .9)
                self.assertEqual(hs.observed_scalar({'float': 1.000000}, option.current), 1.0)
                self.assertEqual(hs.observed_scalar({'float': .9}, option.parse('0.9')), .9)

    def test_other_numeric_options_and_non_numeric_opacities_keep_types(self):
        for name, value in (('general:border_size', 1), ('decoration:other_opacity', 1),
                            (ACTIVE, True), (INACTIVE, '1'), (FULLSCREEN, None)):
            option = hs.Option({'name': name, 'current': value})
            self.assertIs(type(option.current), type(value))
        with self.assertRaises(ValueError):
            hs.Option({'name': 'general:border_size', 'current': 1}).parse('0.9')


if __name__ == '__main__': unittest.main()
