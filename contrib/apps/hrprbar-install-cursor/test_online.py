"""Offline catalog/GUI tests: never apply to the live desktop."""
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRATCH = Path(os.environ.get('TMPDIR', Path.home()/'.cache'/'hrprbar-install-cursor'/'tests'))
SCRATCH.mkdir(parents=True, exist_ok=True)
os.environ.setdefault('TMPDIR', str(SCRATCH))

def package_fixture(names=('',)):
    import struct
    import tarfile
    cursor = (struct.pack('<4I', 0x72756358, 16, 0x10000, 1)
              + struct.pack('<3I', 0xfffd0002, 32, 28)
              + struct.pack('<9I', 36, 0xfffd0002, 32, 1, 1, 1, 0, 0, 0)
              + struct.pack('<I', 0xffffffff))
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:gz') as archive:
        for name in names:
            entry = tarfile.TarInfo((name+'/' if name else '')+'cursors/left_ptr'); entry.size = len(cursor)
            archive.addfile(entry, io.BytesIO(cursor))
    return stream.getvalue()


class Response(io.BytesIO):
    def __init__(self, data, headers=None):
        super().__init__(data)
        self.headers = headers or {}

class CatalogTests(unittest.TestCase):
    def test_latest_release_lists_only_packaged_linux_themes(self):
        import online
        calls = []
        def open_fixture(request, timeout):
            calls.append((request.full_url, timeout))
            names = ['BreezeX-Dark.tar.xz', 'BreezeX.tar.gz', 'BreezeX-Windows.zip', 'bitmaps.zip', 'install.sh']
            body = {'tag_name': 'v2', 'assets': [dict(name=n, size=123, browser_download_url='https://github.com/ful1e5/BreezeX_Cursor/releases/download/v2/'+n, digest=None) for n in names]}
            return Response(json.dumps(body).encode())
        assets = online.latest('https://github.com/ful1e5/BreezeX_Cursor', opener=open_fixture)
        self.assertEqual([a.name for a in assets], ['BreezeX-Dark.tar.xz', 'BreezeX.tar.gz'])
        self.assertEqual(assets[0].repo, 'ful1e5/BreezeX_Cursor')
        self.assertEqual(assets[0].version, 'v2')
        self.assertEqual(calls, [('https://api.github.com/repos/ful1e5/BreezeX_Cursor/releases/latest', 20)])
        self.assertLessEqual({'Bibata', 'BreezeX', 'GoogleDot', 'macOS', 'Fuchsia'}, set(online.FAMILIES))

    def test_aggregate_keeps_other_repositories_when_one_fails(self):
        import online
        calls = []
        def fixture(repo):
            calls.append(repo)
            if repo == online.FAMILIES['macOS']:
                raise ValueError('limite temporário')
            return [online.Asset(repo, 'v1', 'Tema.tar.xz', 100,
                                 'https://github.com/'+repo+'/releases/download/v1/Tema.tar.xz')]
        with patch('online.latest', side_effect=fixture):
            result = online.catalog()
        self.assertEqual(set(calls), set(online.FAMILIES.values()))
        self.assertEqual(len(result.assets), len(online.FAMILIES)-1)
        self.assertEqual({a.repo for a in result.assets}, set(calls)-{online.FAMILIES['macOS']})
        self.assertEqual(len(result.statuses), len(online.FAMILIES))
        self.assertIn('limite temporário', result.statuses[online.FAMILIES['macOS']])
        for repo in set(calls)-{online.FAMILIES['macOS']}:
            self.assertIn('1 pacote', result.statuses[repo])

class BoundaryTests(unittest.TestCase):
    def test_refuses_untrusted_downloads_before_network_or_writes(self):
        import online
        safe = 'https://github.com/owner/repo/releases/download/v1/Tema.tar.gz'
        bad_urls = ['http://github.com/owner/repo/releases/download/v1/Tema.tar.gz',
                    'https://localhost/file', 'https://127.0.0.1/file',
                    'https://github.com.evil.test/file', 'https://user@github.com/owner/repo/releases/download/v1/Tema.tar.gz',
                    'https://github.com:443/owner/repo/releases/download/v1/Tema.tar.gz',
                    'https://github.com/other/repo/releases/download/v1/Tema.tar.gz',
                    'https://github.com/owner/repo/releases/download/../../evil']
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as tmp:
            with patch('online.open_safe', side_effect=AssertionError('unexpected network')):
                for url in bad_urls:
                    with self.subTest(url=url), self.assertRaises(ValueError):
                        online.install_asset(online.Asset('owner/repo', 'v1', 'Tema.tar.gz', 1, url), Path(tmp)/'icons', scratch=Path(tmp))
                for name in ('../escape.tar.gz', '/escape.tar.gz', 'bad\\name.tar.gz', 'x.zip'):
                    with self.subTest(name=name), self.assertRaises(ValueError):
                        online.install_asset(online.Asset('owner/repo', 'v1', name, 1, safe), Path(tmp)/'icons', scratch=Path(tmp))
                for size in (-1, True, online.MAX_DOWNLOAD+1):
                    with self.subTest(size=size), self.assertRaises(ValueError):
                        online.install_asset(online.Asset('owner/repo', 'v1', 'Tema.tar.gz', size, safe), Path(tmp)/'icons', scratch=Path(tmp))
            self.assertEqual(list(Path(tmp).iterdir()), [])

class RedirectTests(unittest.TestCase):
    def test_redirects_checked_before_following(self):
        import online
        from urllib.request import Request
        handler = online.SafeRedirect('owner/repo')
        initial = Request('https://github.com/owner/repo/releases/download/v1/Tema.tar.gz')
        safe = 'https://release-assets.githubusercontent.com/github-production-release-asset/123?signature=abc'
        self.assertEqual(handler.redirect_request(initial, None, 302, 'Found', {}, safe).full_url, safe)
        for url in ('https://localhost/evil', 'http://release-assets.githubusercontent.com/x',
                    'https://user@release-assets.githubusercontent.com/x', 'https://release-assets.githubusercontent.com:443/x',
                    'https://github.com/other/repo/releases/download/v1/x', 'https://api.github.com/x'):
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, 'Redirecionamento'):
                handler.redirect_request(initial, None, 302, 'Found', {}, url)
        api = online.SafeRedirect(None)
        with self.assertRaises(ValueError):
            api.redirect_request(Request('https://api.github.com/repos/o/r/releases/latest'), None, 302, 'Found', {}, 'https://localhost')

class FailureTests(unittest.TestCase):
    def test_catalog_failures_are_actionable_portuguese(self):
        import online
        from urllib.error import HTTPError, URLError
        cases = [(HTTPError('url',404,'Not found',{},None), 'sem releases'),
                 (HTTPError('url',403,'Forbidden',{},None), 'limite'),
                 (HTTPError('url',429,'Too many',{},None), 'limite'),
                 (TimeoutError(), 'Tempo'), (URLError('offline'), 'conexão')]
        for error, message in cases:
            def fail(*args, **kwargs): raise error
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, message):
                online.latest('owner/repo', opener=fail)
            if isinstance(error, HTTPError):
                self.assertTrue(error.closed, 'HTTP error response must be closed')
        for body in (b'not json', b'[]', b'{"assets":{}}', b'{}'):
            with self.subTest(body=body), self.assertRaisesRegex(ValueError, 'catálogo|versão'):
                online.latest('owner/repo', opener=lambda *a, **k: Response(body))
        with self.assertRaisesRegex(ValueError, 'grande'):
            online.latest('owner/repo', opener=lambda *a, **k: Response(b'x'*(online.MAX_METADATA+1)))
        for value in ('http://github.com/o/r', 'https://evil.test/o/r', 'a/b/tree/main', 'o/..', 'o/r?x', 'o/r#x'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                online.repository(value)

    def test_download_rejects_size_hash_and_timeout_without_install(self):
        import online
        from dataclasses import replace
        asset = online.Asset('o/r', 'v1', 'Tema.tar.gz', 4, 'https://github.com/o/r/releases/download/v1/Tema.tar.gz')
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as tmp:
            root = Path(tmp)
            scenarios = [(asset, Response(b'bad'), 'incompleto'),
                         (replace(asset, digest='sha256:'+'0'*64), Response(b'bad!'), 'SHA256'),
                         (asset, Response(b'bad!', {'Content-Length': str(online.MAX_DOWNLOAD+1)}), '64 MiB')]
            with patch('online.cm.install', side_effect=AssertionError('must not install')):
                for entry, response, message in scenarios:
                    with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                        online.install_asset(entry, root/'icons', opener=lambda *a, **k: response, scratch=root)
                with patch('online.MAX_DOWNLOAD', 3):
                    with self.assertRaises(ValueError):
                        online.install_asset(asset, root/'icons', opener=lambda *a, **k: Response(b'long'), scratch=root)
                def timedout(*args, **kwargs): raise TimeoutError()
                with self.assertRaisesRegex(ValueError, 'Tempo'):
                    online.install_asset(asset, root/'icons', opener=timedout, scratch=root)
            self.assertEqual(list(root.iterdir()), [])

class DownloadTests(unittest.TestCase):
    def test_invalid_catalog_assets_are_not_offered_for_installation(self):
        import online
        cases = [None, {}, {'name': 42}, {'name': 'Tema.tar.xz'},
                 {'name': 'Tema.tar.xz', 'size': 100, 'browser_download_url': 'https://localhost/file'},
                 {'name': '../escape.tar.xz', 'size': 100, 'browser_download_url': 'https://github.com/o/r/releases/download/v1/escape.tar.xz'}]
        for item in cases:
            with self.subTest(item=item), self.assertRaisesRegex(ValueError, 'catálogo|pacotes'):
                online.latest('o/r', opener=lambda *a, **k: Response(json.dumps({'tag_name':'v1', 'assets':[item]}).encode()))

    def test_download_validates_installs_flat_theme_and_cleans_package(self):
        import online
        import hashlib
        import struct
        import tarfile
        # One real, decodable Xcursor image, generated without desktop inputs.
        cursor = (struct.pack('<4I', 0x72756358, 16, 0x10000, 1)
                  + struct.pack('<3I', 0xfffd0002, 32, 28)
                  + struct.pack('<9I', 36, 0xfffd0002, 32, 1, 1, 1, 0, 0, 0)
                  + struct.pack('<I', 0xffffffff))
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w:gz') as archive:
            entry = tarfile.TarInfo('cursors/left_ptr'); entry.size = len(cursor)
            archive.addfile(entry, io.BytesIO(cursor))
        data = stream.getvalue()
        asset = online.Asset('owner/repo', 'v1', 'Tema.tar.gz', len(data),
                             'https://github.com/owner/repo/releases/download/v1/Tema.tar.gz',
                             'sha256:'+hashlib.sha256(data).hexdigest())
        seen = []
        def open_fixture(request, timeout):
            seen.append(request.full_url)
            return Response(data, {'Content-Length': str(len(data))})
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as tmp:
            root = Path(tmp)
            result = online.install_asset(asset, root/'icons', opener=open_fixture, scratch=root)
            self.assertEqual(result, [root/'icons'/'Tema'])
            self.assertEqual((result[0]/'cursors'/'left_ptr').read_bytes(), cursor)
            self.assertEqual(sorted(p.name for p in root.iterdir()), ['icons'])
            with self.assertRaisesRegex(FileExistsError, 'já instalado'):
                online.install_asset(asset, root/'icons', opener=open_fixture, scratch=root)
            self.assertEqual(sorted(p.name for p in root.iterdir()), ['icons'])
        self.assertEqual(seen, [asset.url, asset.url])

@unittest.skipUnless(os.environ.get('DISPLAY'), 'GUI requires DISPLAY')
class OnlineGuiTests(unittest.TestCase):
    def setUp(self):
        import app
        import tkinter as tk
        self.module = app
        self.root = tk.Tk(); self.root.withdraw()
        self.addCleanup(self.cleanup_root)
        self.real_discover = app.cm.discover
        self.discovery = self.enterContext(patch('app.cm.discover', return_value=[]))
        self.enterContext(patch('app.App.refresh_palette'))
        self.apply = self.enterContext(patch('app.settings.apply', side_effect=AssertionError('desktop apply forbidden')))
        self.app = app.App(self.root)
        self.pump(lambda: self.app.status.get().startswith('0 temas'))

    def cleanup_root(self):
        for identifier in self.root.tk.call('after', 'info'):
            self.root.after_cancel(identifier)
        self.root.destroy()

    def pump(self, predicate):
        import time
        deadline = time.monotonic()+5
        while time.monotonic() < deadline:
            self.root.update()
            if predicate(): return
            time.sleep(.01)
        self.fail('GUI worker timed out')

    def test_download_install_refresh_select_then_only_explicit_apply(self):
        import online
        data = package_fixture()
        asset = online.Asset('o/r', 'v1', 'Tema.tar.gz', len(data), 'https://github.com/o/r/releases/download/v1/Tema.tar.gz')
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as tmp:
            dest = Path(tmp)/'icons'
            self.discovery.side_effect = lambda: self.real_discover([dest])
            with patch.dict(os.environ, {'XDG_DATA_HOME': tmp}), patch('online.latest', return_value=[asset]), patch('online.open_safe', side_effect=lambda *a: Response(data)), patch('app.messagebox.askyesno', return_value=True) as confirm:
                self.app.open_online(); dialog = self.app.online_dialog
                dialog.repo.set('o/r'); dialog.fetch(); self.pump(lambda: not self.app.busy)
                dialog.tree.selection_set('0'); self.root.update()
                dialog.install_selected()
                self.pump(lambda: self.app.selected is not None and self.app.rendered > 0 and not self.app.busy)
                self.assertEqual(self.app.selected.name, 'Tema')
                self.assertTrue((dest/'Tema/cursors/left_ptr').is_file())
                self.assertEqual(self.app.size.get(), '32')
                self.assertEqual(tuple(self.app.size_box.cget('values')), ('32',))
                self.apply.assert_not_called()
                self.assertFalse(self.app.applied)
                self.assertIn('Nada foi aplicado', self.app.status.get())
                confirm.return_value = False
                self.app.do_apply()
                self.apply.assert_not_called()
                confirm.return_value = True
                self.apply.side_effect = None; self.apply.return_value = 'VERIFICADO (isolated test double)'
                self.app.do_apply(); self.pump(lambda: not self.app.busy)
                self.apply.assert_called_once_with(self.app.selected, 32)

    def test_late_discovery_cannot_replace_post_install_refresh(self):
        import threading
        entered = threading.Event(); release = threading.Event()
        self.addCleanup(release.set)
        old = self.module.cm.Theme('Old', Path('/nonexistent'), True, False)
        new = self.module.cm.Theme('New', Path('/nonexistent'), True, False)
        def first():
            entered.set(); release.wait(4); return [old]
        with patch('app.cm.discover', side_effect=first):
            self.app.load(); self.assertTrue(entered.wait(2))
            with patch('app.cm.discover', return_value=[new]):
                self.app.load(['New'])
                self.pump(lambda: self.app.selected is not None and self.app.selected.name == 'New')
            release.set()
            import time
            end = time.monotonic()+.2
            self.pump(lambda: time.monotonic() > end)
            self.assertEqual([t.name for t in self.app.themes], ['New'])

    def test_collection_refresh_clears_old_selection_until_user_chooses(self):
        cm = self.module.cm
        old = cm.Theme('Old', Path('/nonexistent'), True, False)
        self.app.selected = old
        themes = [cm.Theme(name, Path('/nonexistent')/name, True, False) for name in ('A','B')]
        self.app.loaded(themes, None, ['A','B'])
        self.root.update()
        self.assertIsNone(self.app.selected)
        self.assertEqual(self.app.tree.selection(), ())
        self.assertTrue(self.app.apply_button.instate(['disabled']))
        self.assertIn('Escolha', self.app.heading.cget('text'))
        self.assertIn('A', self.app.status.get()); self.assertIn('B', self.app.status.get())
        self.apply.assert_not_called()

    def test_concurrent_requests_and_stale_results_cannot_install_or_apply(self):
        import threading
        import online
        entered = threading.Event(); release = threading.Event()
        self.addCleanup(release.set)
        asset = online.Asset('o/r', 'v1', 'Tema.tar.gz', 100, 'https://github.com/o/r/releases/download/v1/Tema.tar.gz')
        def fixture(repo):
            entered.set(); release.wait(4); return [asset]
        with patch('online.latest', side_effect=fixture) as fetch, patch('online.install_asset') as install, patch('app.messagebox.askyesno') as confirm:
            self.app.open_online(); dialog = self.app.online_dialog
            dialog.repo.set('o/r'); dialog.fetch()
            self.assertTrue(entered.wait(2))
            self.assertTrue(self.app.busy)
            dialog.fetch(); dialog.install_selected(); dialog.close()
            self.assertTrue(dialog.window.winfo_exists())
            self.app.selected = self.module.cm.Theme('Old', Path('/nonexistent'), True, False)
            self.app.do_apply()
            confirm.assert_not_called()
            dialog.repo.set('other/repo')
            release.set(); self.pump(lambda: not self.app.busy)
            self.assertEqual(dialog.tree.get_children(), ())
            self.assertTrue(dialog.install_button.instate(['disabled']))
            self.assertEqual(fetch.call_count, 1)
            install.assert_not_called(); self.apply.assert_not_called()

    def test_all_presets_active_by_default_and_individual_sources_wired(self):
        import online
        def fixture(repo):
            return [online.Asset(repo, 'v1', 'Tema.tar.xz', 100,
                                 'https://github.com/'+repo+'/releases/download/v1/Tema.tar.xz')]
        with patch('online.latest', side_effect=fixture) as fetch:
            self.app.open_online(); dialog = self.app.online_dialog
            self.assertEqual(dialog.family.get(), 'Todos os repositórios')
            from tkinter import ttk
            self.assertLessEqual(int(ttk.Style(self.root).lookup(dialog.tree.cget('style') or 'Treeview', 'rowheight')), 36)
            fetch.assert_not_called()
            dialog.fetch_button.invoke()
            self.pump(lambda: not self.app.busy)
            self.assertEqual(fetch.call_count, len(online.FAMILIES))
            self.assertEqual(len(dialog.tree.get_children()), len(online.FAMILIES))
            for repo in online.FAMILIES.values():
                self.assertIn(repo, dialog.status.get())
            for name, repo in online.FAMILIES.items():
                dialog.family.set(name); dialog.select_family()
                self.assertEqual(dialog.repo.get(), repo)
                dialog.fetch_button.invoke(); self.pump(lambda: not self.app.busy)
                self.assertEqual(len(dialog.tree.get_children()), 1)
                self.assertEqual(dialog.assets[0].repo, repo)
            self.assertEqual(fetch.call_count, 2*len(online.FAMILIES))
        self.apply.assert_not_called()

    def test_open_fetch_filter_and_invalidate_selection_through_real_queue(self):
        import online
        assets = [online.Asset('owner/repo', 'v2', n, 123, 'https://github.com/owner/repo/releases/download/v2/'+n)
                  for n in ('Tema-Dark.tar.xz', 'Tema-Light.tar.xz')]
        with patch('online.latest', return_value=assets) as fetch:
            self.app.online_button.invoke()
            dialog = self.app.online_dialog
            self.assertEqual(fetch.call_count, 0, 'opening must not contact network')
            self.assertGreaterEqual(dialog.window.winfo_width(), 900)
            dialog.repo.set('owner/repo')
            dialog.fetch_button.invoke()
            self.pump(lambda: not self.app.busy)
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(len(dialog.tree.get_children()), 2)
            self.assertIn('v2', str(dialog.tree.item(dialog.tree.get_children()[0], 'values')))
            self.assertIn('owner/repo', dialog.status.get())
            dialog.search.set('Dark')
            self.assertEqual(len(dialog.tree.get_children()), 1)
            dialog.tree.selection_set(dialog.tree.get_children()[0]); self.root.update()
            self.assertFalse(dialog.install_button.instate(['disabled']))
            dialog.repo.set('other/repo')
            self.assertEqual(dialog.tree.get_children(), ())
            self.assertTrue(dialog.install_button.instate(['disabled']))
        self.apply.assert_not_called()

if __name__ == '__main__':
    unittest.main()
