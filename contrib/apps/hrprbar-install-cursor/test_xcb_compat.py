"""Legacy XCB fallback tests: isolated homes only, never desktop commands."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cursor_manager as cm
import settings


class XcbCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ['TMPDIR'])
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.source = self.home / '.local/share/icons/macOS'
        self.source.mkdir(parents=True)
        self.theme = cm.Theme('macOS', self.source, True, False)

    def test_external_theme_alias_and_exact_default_backup(self):
        default = self.home / '.icons/default/index.theme'
        default.parent.mkdir(parents=True)
        original = '# keep comment\n[Icon Theme]\nName=Keep\nInherits=hyprbar\nHidden=true\n\n[Other]\nInherits=untouched\n'
        default.write_text(original)
        diagnostics = settings.prepare_xcb_theme(self.theme, self.home)
        alias = self.home / '.icons/macOS'
        self.assertTrue(alias.is_symlink())
        self.assertEqual(alias.resolve(), self.source)
        self.assertEqual(default.read_text(), original.replace('Inherits=hyprbar', 'Inherits=macOS'))
        backups = list(default.parent.glob('index.theme.bak-*'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), original)
        self.assertTrue(any(str(alias) in line for line in diagnostics))
        self.assertTrue(any(str(backups[0]) in line for line in diagnostics))
        self.assertEqual(list(self.source.iterdir()), [])
        settings.prepare_xcb_theme(self.theme, self.home)
        self.assertEqual(len(list(default.parent.glob('index.theme.bak-*'))), 1)

    def test_unsafe_names_rejected_before_writes(self):
        for name in ('.', '..', '../escape', '/absolute', 'a/b', 'a\\b', 'bad\nname', ' leading', 'trailing '):
            with self.subTest(name=name), self.assertRaises(ValueError):
                settings.prepare_xcb_theme(cm.Theme(name, self.source, True, False), self.home)
        self.assertFalse((self.home / '.icons').exists())

    def test_conflicting_existing_alias_is_never_replaced(self):
        alias = self.home / '.icons/macOS'
        alias.mkdir(parents=True)
        (alias / 'keep').write_text('unchanged')
        with self.assertRaisesRegex(ValueError, 'conflit'):
            settings.prepare_xcb_theme(self.theme, self.home)
        self.assertEqual((alias / 'keep').read_text(), 'unchanged')
        alias.rename(alias.with_name('other'))
        alias.symlink_to(alias.with_name('other'))
        with self.assertRaisesRegex(ValueError, 'conflit'):
            settings.prepare_xcb_theme(self.theme, self.home)
        self.assertTrue(alias.is_symlink())
        self.assertFalse((self.home / '.icons/default').exists())

    def test_failed_atomic_write_rolls_back_new_alias(self):
        default = self.home / '.icons/default/index.theme'
        default.parent.mkdir(parents=True)
        default.write_text('[Icon Theme]\nInherits=old\n')
        with patch('settings.os.replace', side_effect=OSError('write blocked')):
            with self.assertRaisesRegex(OSError, 'write blocked'):
                settings.prepare_xcb_theme(self.theme, self.home)
        self.assertFalse((self.home / '.icons/macOS').is_symlink())
        self.assertEqual(default.read_text(), '[Icon Theme]\nInherits=old\n')

    def test_default_name_is_discoverable_without_self_cycle_or_source_edit(self):
        index = self.source / 'index.theme'
        index.write_text('[Icon Theme]\nName=Actual default\n')
        settings.prepare_xcb_theme(cm.Theme('default', self.source, True, False), self.home)
        self.assertEqual(index.read_text(), '[Icon Theme]\nName=Actual default\n')
        self.assertEqual((self.home / '.icons/default').resolve(), self.source)

    def test_default_symlink_preserved_and_actual_target_backed_up(self):
        target = self.home / 'dotfiles/default.theme'
        target.parent.mkdir()
        target.write_text('[Icon Theme]\nInherits=old\n[Other]\nKeep=yes\n')
        default = self.home / '.icons/default/index.theme'
        default.parent.mkdir(parents=True)
        default.symlink_to(target)
        settings.prepare_xcb_theme(self.theme, self.home)
        self.assertTrue(default.is_symlink())
        self.assertEqual(default.resolve(), target)
        self.assertIn('Inherits=macOS', target.read_text())
        self.assertEqual(next(target.parent.glob('default.theme.bak-*')).read_text(), '[Icon Theme]\nInherits=old\n[Other]\nKeep=yes\n')

    def test_invalid_metadata_rolls_back_new_alias(self):
        default = self.home / '.icons/default/index.theme'
        default.parent.mkdir(parents=True)
        default.write_bytes(b'\xff')
        with self.assertRaises(UnicodeError):
            settings.prepare_xcb_theme(self.theme, self.home)
        self.assertFalse((self.home / '.icons/macOS').is_symlink())

    def test_refuse_default_target_inside_selected_source(self):
        index = self.source / 'index.theme'
        index.write_text('[Icon Theme]\nName=Untouched\n')
        default = self.home / '.icons/default'
        default.parent.mkdir()
        default.symlink_to(self.source)
        with self.assertRaisesRegex(ValueError, 'origem'):
            settings.prepare_xcb_theme(self.theme, self.home)
        self.assertFalse((self.home / '.icons/macOS').is_symlink())
        self.assertEqual(index.read_text(), '[Icon Theme]\nName=Untouched\n')

    def test_every_apply_updates_fallback_and_keeps_prior_alias(self):
        config = self.home / '.config/hypr'
        config.mkdir(parents=True)
        (config / 'hyprland.lua').write_text('hl.config({cursor={enable_hyprcursor=true}})\n')
        calls = []
        def runner(args, data=None):
            calls.append((args, data))
            return True, '[]' if args[:2] == ['hyprctl', 'monitors'] else ''
        first = settings.apply(self.theme, 28, home=self.home, runner=runner, inspect_apps=False)
        second_source = self.home / '.local/share/icons/Second'
        second_source.mkdir()
        second = settings.apply(cm.Theme('Second', second_source, True, False), 32, home=self.home, runner=runner, inspect_apps=False)
        self.assertEqual((self.home / '.icons/macOS').resolve(), self.source)
        self.assertEqual((self.home / '.icons/Second').resolve(), second_source)
        self.assertIn('Inherits=Second', (self.home / '.icons/default/index.theme').read_text())
        for report in (first, second):
            self.assertIn('VERIFICADO fallback XCB (arquivos)', report)
            self.assertIn('NÃO comprova o cursor visual', report)
        self.assertIn((['xrdb', '-merge'], 'Xcursor.theme: Second\nXcursor.size: 32\n'), calls)

    def test_readback_failure_restores_default_and_removes_new_alias(self):
        default = self.home / '.icons/default/index.theme'
        default.parent.mkdir(parents=True)
        original = b'[Icon Theme]\nInherits=old\n'
        default.write_bytes(original)
        real_read = Path.read_bytes
        reads = []
        def read(path):
            if path == default:
                reads.append(path)
                if len(reads) == 2:
                    return b'wrong readback'
            return real_read(path)
        with patch.object(Path, 'read_bytes', read):
            with self.assertRaisesRegex(OSError, 'verifica'):
                settings.prepare_xcb_theme(self.theme, self.home)
        self.assertEqual(default.read_bytes(), original)
        self.assertFalse((self.home / '.icons/macOS').is_symlink())

    def test_live_runner_selects_matching_wayland_instance(self):
        from subprocess import CompletedProcess
        instances = '[{"instance":"stale","wl_socket":"wayland-9"},{"instance":"live-signature","wl_socket":"wayland-1"}]'
        with patch.dict(os.environ, {'WAYLAND_DISPLAY': 'wayland-1', 'HYPRLAND_INSTANCE_SIGNATURE': 'stale'}):
            with patch('settings.subprocess.run', side_effect=[CompletedProcess([], 0, instances, ''), CompletedProcess([], 0, 'done', '')]) as boundary:
                self.assertEqual(settings.run(['hyprctl', 'setcursor', 'macOS', '28']), (True, 'done'))
        self.assertEqual(boundary.call_args_list[0].args[0], ['hyprctl', 'instances', '-j'])
        self.assertEqual(boundary.call_args_list[1].args[0], ['hyprctl', '-i', 'live-signature', 'setcursor', 'macOS', '28'])

    def test_live_runner_refuses_ambiguous_or_missing_matching_instance(self):
        from subprocess import CompletedProcess
        for instances in ('[]', '[{"instance":"a","wl_socket":"wayland-1"},{"instance":"b","wl_socket":"wayland-1"}]', 'not json'):
            with self.subTest(instances=instances), patch.dict(os.environ, {'WAYLAND_DISPLAY': 'wayland-1'}):
                with patch('settings.subprocess.run', return_value=CompletedProcess([], 0, instances, '')) as boundary:
                    ok, diagnostic = settings.run(['hyprctl', 'reload'])
            self.assertFalse(ok)
            self.assertIn('Hyprland', diagnostic)
            self.assertEqual(boundary.call_count, 1)

    def test_existing_legacy_source_requires_no_alias(self):
        source = self.home / '.icons/Native'
        source.mkdir(parents=True)
        source_index = source / 'index.theme'
        source_index.write_text('[Icon Theme]\nName=Native\n')
        settings.prepare_xcb_theme(cm.Theme('Native', source, True, False), self.home)
        self.assertFalse(source.is_symlink())
        self.assertEqual(source_index.read_text(), '[Icon Theme]\nName=Native\n')
        self.assertIn('Inherits=Native', (self.home / '.icons/default/index.theme').read_text())

    def test_default_directory_failure_creates_no_alias(self):
        default = self.home / '.icons/default'
        default.parent.mkdir()
        default.symlink_to(self.home / 'missing-parent/default')
        with self.assertRaises(OSError):
            settings.prepare_xcb_theme(self.theme, self.home)
        self.assertFalse((self.home / '.icons/macOS').is_symlink())

    def test_default_directory_symlink_to_other_cursor_source_refused(self):
        other = self.home / '.local/share/icons/Other'
        (other / 'cursors').mkdir(parents=True)
        index = other / 'index.theme'
        index.write_text('[Icon Theme]\nName=Other\n')
        default = self.home / '.icons/default'
        default.parent.mkdir()
        default.symlink_to(other)
        with self.assertRaisesRegex(ValueError, 'origem'):
            settings.prepare_xcb_theme(self.theme, self.home)
        self.assertEqual(index.read_text(), '[Icon Theme]\nName=Other\n')
        self.assertFalse((self.home / '.icons/macOS').is_symlink())


if __name__ == '__main__':
    unittest.main()
