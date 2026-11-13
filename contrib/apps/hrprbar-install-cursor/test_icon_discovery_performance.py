"""Discovery stays bounded; installation/application keep complete link audits."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
import icons


class FastIconDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = self.enterContext(tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']))
        self.base = Path(self.temp)
        self.theme = self.base/'themes'/'Example'
        folder = self.theme/'32x32/apps'
        folder.mkdir(parents=True)
        (self.theme/'index.theme').write_text('[Icon Theme]\nName=Example\nDirectories=32x32/apps\n\n[32x32/apps]\nSize=32\nType=Fixed\n')
        Image.new('RGBA', (32, 32), '#123456').save(folder/'demo.png')

    def test_listing_bounds_entries_examined_in_each_icon_root(self):
        root = self.theme.parent
        for index in range(300):
            (root/f'other-{index:03}').mkdir()
        original = os.scandir
        examined = []

        class CountingScan:
            def __init__(self, scan): self.scan = scan
            def __enter__(self): return self
            def __exit__(self, *args): self.scan.close()
            def __iter__(self): return self
            def __next__(self):
                item = next(self.scan)
                examined.append(item.name)
                return item

        def count_root_entries(directory):
            scan = original(directory)
            try:
                is_root = (os.fstat(directory).st_ino == root.stat().st_ino
                           if isinstance(directory, int) else Path(directory) == root)
            except OSError:
                is_root = False
            return CountingScan(scan) if is_root else scan

        with patch('icons.os.scandir', side_effect=count_root_entries):
            icons.discover([root])
        self.assertEqual(len(examined), 256)

    def test_discovery_does_not_recursively_audit_installed_themes(self):
        # Listing must not wait for a tree-wide walk over thousands of aliases.
        with patch('icons.os.walk', side_effect=AssertionError('expensive recursive audit during listing')):
            found = icons.discover([self.theme.parent])
        self.assertEqual([theme.name for theme in found], ['Example'])
        self.assertTrue(found[0].samples)
        self.assertTrue(all(path.resolve().is_relative_to(self.theme) for path in found[0].samples))


    def test_listing_stops_scanning_samples_after_twelve(self):
        folder = self.theme/'32x32/apps'
        image = (folder/'demo.png').read_bytes()
        for i in range(40):
            (folder/f'icon-{i}.png').write_bytes(image)
        original = os.scandir
        examined = []

        class CountingScan:
            def __init__(self, scan): self.scan = scan
            def __enter__(self): return self
            def __exit__(self, *args): self.scan.close()
            def __iter__(self): return self
            def __next__(self):
                item = next(self.scan)
                examined.append(item.name)
                return item

        def entries(directory):
            scan = original(directory)
            if isinstance(directory, int) and os.fstat(directory).st_ino == folder.stat().st_ino:
                return CountingScan(scan)
            return scan

        with patch('icons.os.scandir', side_effect=entries):
            found = icons.discover([self.theme.parent])
        self.assertEqual(len(found[0].samples), 12)
        self.assertEqual(len(examined), 12, 'Listing kept traversing images after collecting its samples')

    def test_hidden_unsafe_link_is_rejected_before_apply_or_install(self):
        from unittest.mock import Mock
        hidden = self.theme/'unlisted'
        hidden.mkdir()
        outside = self.base/'external.png'
        outside.write_bytes((self.theme/'32x32/apps/demo.png').read_bytes())
        (hidden/'escape.png').symlink_to(outside)
        found = icons.discover([self.theme.parent])
        self.assertEqual(len(found), 1)
        self.assertTrue(all(path.resolve().is_relative_to(self.theme) for path in found[0].samples))
        runner = Mock(side_effect=AssertionError('unsafe theme must be rejected before settings access'))
        with self.assertRaises(ValueError):
            icons.apply(found[0], home=self.base/'home', runner=runner)
        runner.assert_not_called()
        self.assertFalse((self.base/'home').exists())
        with self.assertRaises(ValueError):
            icons.install(self.theme, self.base/'installed')
        self.assertFalse((self.base/'installed/Example').exists())

    def test_complete_audit_detects_entry_replaced_by_external_link(self):
        hidden = self.theme/'hidden.dat'
        hidden.write_text('ordinary file')
        outside = self.base/'secret.dat'
        outside.write_text('outside')
        original_stat = os.stat
        replaced = False

        def replace_after_lstat(path, *args, **kwargs):
            nonlocal replaced
            info = original_stat(path, *args, **kwargs)
            if path == hidden.name and kwargs.get('dir_fd') is not None and not replaced:
                replaced = True
                hidden.unlink()
                hidden.symlink_to(outside)
            return info

        with patch('icons.os.stat', side_effect=replace_after_lstat):
            with self.assertRaises(ValueError):
                icons.validate_theme(self.theme)
        self.assertTrue(replaced)

    def test_listing_does_not_read_an_external_sample(self):
        outside = self.base/'external.png'
        outside.write_bytes((self.theme/'32x32/apps/demo.png').read_bytes())
        (self.theme/'32x32/apps/escape.png').symlink_to(outside)
        original = Image.open
        opened = []
        def checked(path, *args, **kwargs):
            opened.append(Path(os.readlink(f'/proc/self/fd/{path.fileno()}')) if hasattr(path, 'fileno') else Path(path).resolve())
            return original(path, *args, **kwargs)
        with patch('PIL.Image.open', side_effect=checked):
            self.assertEqual(icons.discover([self.theme.parent]), [])
        self.assertNotIn(outside, opened)

    def test_listing_rejects_external_metadata(self):
        metadata = self.theme/'index.theme'
        outside = self.base/'external.theme'
        metadata.rename(outside)
        metadata.symlink_to(outside)
        self.assertEqual(icons.discover([self.theme.parent]), [])

    def test_listing_keeps_internal_sample_alias_inside_theme(self):
        folder = self.theme/'32x32/apps'
        image = folder/'demo.png'
        safe = self.theme/'safe.png'
        image.rename(safe)
        image.symlink_to('../../safe.png')
        outside = self.base/'external.png'
        Image.new('RGBA', (32, 32), '#abcdef').save(outside)
        found = icons.discover([self.theme.parent])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].samples, (image,))
        self.assertTrue(found[0].samples[0].is_relative_to(found[0].path))

    def test_listing_does_not_follow_target_replaced_after_resolution(self):
        folder = self.theme/'32x32/apps'
        image = folder/'demo.png'
        safe = self.theme/'safe.png'
        image.rename(safe)
        image.symlink_to('../../safe.png')
        outside = self.base/'external.png'
        Image.new('RGBA', (32, 32), '#abcdef').save(outside)
        original = icons._open_relative
        replaced = False

        def replace_target_after_listing(root_fd, relative, flags, resolve=icons._RESOLVE_BENEATH | icons._RESOLVE_NO_MAGICLINKS):
            nonlocal replaced
            if relative == '32x32/apps/demo.png' and not replaced:
                replaced = True
                image.unlink()
                image.symlink_to(outside)
            return original(root_fd, relative, flags, resolve)

        with patch('icons._open_relative', side_effect=replace_target_after_listing):
            self.assertEqual(icons.discover([self.theme.parent]), [])
        self.assertTrue(replaced)

    def test_listing_keeps_pinned_theme_root_when_path_is_replaced(self):
        original = icons._open_relative
        saved = self.base/'saved-theme'
        replacement_image = self.base/'replacement.png'
        Image.new('RGBA', (32, 32), '#abcdef').save(replacement_image)
        swapped = False

        def replace_after_root_pin(root_fd, relative, flags, resolve=icons._RESOLVE_BENEATH | icons._RESOLVE_NO_MAGICLINKS):
            nonlocal swapped
            if relative == 'index.theme' and not swapped:
                swapped = True
                self.theme.rename(saved)
                (self.theme/'32x32/apps').mkdir(parents=True)
                (self.theme/'index.theme').write_text('[Icon Theme]\nName=Replacement\nDirectories=32x32/apps\n\n[32x32/apps]\nSize=32\nType=Fixed\n')
                (self.theme/'32x32/apps/replacement.png').symlink_to(replacement_image)
            return original(root_fd, relative, flags, resolve)

        with patch('icons._open_relative', side_effect=replace_after_root_pin):
            found = icons.discover([self.theme.parent])
        self.assertTrue(swapped)
        self.assertEqual([theme.label for theme in found], ['Example'])

    def test_listing_rejects_external_declared_directory(self):
        folder = self.theme/'32x32/apps'
        outside = self.base/'external-apps'
        folder.rename(outside)
        folder.symlink_to(outside, target_is_directory=True)
        self.assertEqual(icons.discover([self.theme.parent]), [])

    def test_listing_does_not_enumerate_declared_folder_replaced_outside(self):
        folder = self.theme/'32x32/apps'
        moved = self.base/'moved-apps'
        outside = self.base/'external-apps'
        outside.mkdir()
        (outside/'external.png').write_bytes((folder/'demo.png').read_bytes())
        original_open = icons._open_relative
        original_scandir = os.scandir
        enumerated = []
        swapped = False

        def replace_before_directory_open(root_fd, relative, flags, resolve=icons._RESOLVE_BENEATH | icons._RESOLVE_NO_MAGICLINKS):
            nonlocal swapped
            if relative == '32x32/apps' and not swapped:
                swapped = True
                folder.rename(moved)
                folder.symlink_to(outside, target_is_directory=True)
            return original_open(root_fd, relative, flags, resolve)

        def track_scandir(directory):
            if isinstance(directory, int):
                actual = Path(os.readlink(f'/proc/self/fd/{directory}'))
                if actual == outside:
                    enumerated.append(actual)
            return original_scandir(directory)

        with patch('icons._open_relative', side_effect=replace_before_directory_open), patch('icons.os.scandir', side_effect=track_scandir):
            self.assertEqual(icons.discover([self.theme.parent]), [])
        self.assertTrue(swapped)
        self.assertNotIn(outside, enumerated)

    def test_listing_bounds_invalid_and_non_image_entries(self):
        """At most 256 directory entries are inspected per declared directory."""
        folder = self.theme/'32x32/apps'
        for i in range(400):
            (folder/f'junk-{i}.txt').touch()
        original = os.scandir
        examined = []

        class CountingScan:
            def __init__(self, scan): self.scan = scan
            def __enter__(self): return self
            def __exit__(self, *args): self.scan.close()
            def __iter__(self): return self
            def __next__(self):
                item = next(self.scan)
                examined.append(item.name)
                return item

        def count_entries(directory):
            scan = original(directory)
            if isinstance(directory, int) and os.fstat(directory).st_ino == folder.stat().st_ino:
                return CountingScan(scan)
            return scan

        with patch('icons.os.scandir', side_effect=count_entries):
            found = icons.discover([self.theme.parent])
        self.assertEqual([theme.name for theme in found], ['Example'])
        self.assertEqual(len(examined), icons.MAX_ENTRIES_PER_DIRECTORY)

    def test_disappearing_sample_symlink_does_not_discard_other_samples(self):
        folder = self.theme/'32x32/apps'
        second = folder/'other.png'
        Image.new('RGBA', (32, 32), '#abcdef').save(second)
        disappearing = folder/'gone.png'
        disappearing.symlink_to('missing.png')
        found = icons.discover([self.theme.parent])
        self.assertEqual(len(found), 1)
        self.assertIn(second, found[0].samples)

    def test_preview_open_is_anchored_to_theme_after_sample_retarget(self):
        theme = icons.discover([self.theme.parent])[0]
        sample = theme.samples[0]
        outside = self.base/'external.png'
        Image.new('RGBA', (32, 32), '#abcdef').save(outside)
        sample.unlink()
        sample.symlink_to(outside)
        with self.assertRaises((ValueError, OSError)):
            icons.preview(sample, root=theme.path, root_identity=theme.root_identity)

    def test_apply_refuses_theme_root_replaced_since_listing(self):
        import shutil
        from unittest.mock import Mock
        theme = icons.discover([self.theme.parent])[0]
        staged = self.base/'replacement-theme'
        saved = self.base/'original-theme'
        shutil.copytree(theme.path, staged)
        theme.path.rename(saved)
        staged.rename(theme.path)
        runner = Mock(return_value=(True, "'previous'"))
        with self.assertRaises(ValueError):
            icons.apply(theme, home=self.base/'home', runner=runner)
        runner.assert_not_called()


if __name__ == '__main__':
    unittest.main()
