"""Offline curated icon catalog and bounded installation tests."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch

from PIL import Image
import icons
import installer
import online

if importlib.util.find_spec('icon_catalog'):
    import icon_catalog as catalog
else:
    catalog = None


class Catalog(unittest.TestCase):
    def test_exact_curated_catalog_and_pinned_provenance(self):
        self.assertIsNotNone(catalog, 'curated icon backend missing')
        expected = (
            ('mint-light', 'Mint Breeze Light Icons', 'dr-mccoy', '2326678', 'GPL-3.0', 'Bloqueado: pacote 1.4.20 contém link quebrado (apps/48/plasma-browser-integration.svg).'),
            ('nordic-slot', 'Nordic Slot Dark Icons', 'l4k1', '2378240', 'GPL-3.0', 'Bloqueado: 36.217 entradas excedem o limite de 20.000.'),
            ('buuf', 'Buuf For Many Desktops', 'nestort', '1012233', 'Divergente: site CC-BY-SA; upstream cita CC-BY-NC-SA 2.5', 'Bloqueado: pacote excede 64 MiB; licença precisa de revisão.'),
            ('neoline', 'NeoLine', 'Morzilla', '2381562', 'MIT', 'Verificado: NeoLine, NeoLine-White e NeoLine-Yellow; requer fallback Breeze Dark.'),
            ('skeuo-art-deco', 'Skeuo-Silver-Art-Deco', 'artsailer', '2376237', 'GPL-3.0', 'Bloqueado: pacote declarado 167.658 KiB excede 64 MiB.'),
            ('mint-calm', 'Mint Breeze - Calm Green Icons', 'dr-mccoy', '2324617', 'GPL-3.0', 'Bloqueado: pacote 1.4.20 contém dois links quebrados.'),
        )
        self.assertIsInstance(catalog.SOURCES, tuple)
        self.assertEqual(len(catalog.SOURCES), 6)
        self.assertEqual(len({s.key for s in catalog.SOURCES}), 6)
        for source, row in zip(catalog.SOURCES, expected):
            key, name, author, product, license, reason = row
            self.assertEqual((source.key, source.name, source.author, source.page, source.license, source.reason),
                             (key, name, author, f'https://www.gnome-look.org/p/{product}/', license, reason))
            with self.assertRaises(FrozenInstanceError):
                source.key = 'changed'
        self.assertEqual([s.key for s in catalog.SOURCES if s.package], ['neoline'])
        package = catalog.SOURCES[3].package
        self.assertEqual((package.repo, package.commit, package.name, package.size, package.sha256),
                         ('Morzilla/neoline-icons', '30abd1093bf2ddc3689474a4ca94c53fb21ae74e', 'NeoLine.tar.gz', 2005766,
                          '61dc114ec3cf6c15e36a2387f0c34d95246c13c4d07c9ed7551f9ce3c5d60ec8'))
        self.assertEqual(package.url, 'https://codeload.github.com/Morzilla/neoline-icons/tar.gz/30abd1093bf2ddc3689474a4ca94c53fb21ae74e')
        with self.assertRaises(FrozenInstanceError):
            package.size = 1


class Admission(unittest.TestCase):
    def test_blocked_and_nonidentical_sources_never_open_network(self):
        self.assertTrue(hasattr(catalog, 'install_source'), 'secure source installer missing')
        trusted = catalog.SOURCES[3]
        candidates = [s for s in catalog.SOURCES if s.package is None]
        candidates += [replace(trusted), replace(trusted, name='forged'),
                       replace(trusted, package=replace(trusted.package, repo='attacker/repo')), None]
        opener = Mock(side_effect=AssertionError('network must not be opened'))
        for source in candidates:
            with self.subTest(source=source):
                with self.assertRaises(ValueError):
                    catalog.install_source(source, Path('/not-used'), opener=opener)
        opener.assert_not_called()


class Response(io.BytesIO):
    def __init__(self, body, headers=None, status=200, url=None):
        super().__init__(body)
        self.headers = headers or {}
        self.status = status
        self.url = url

    def geturl(self):
        return self.url


class Downloads(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.scratch = self.base/'scratch'
        self.scratch.mkdir()
        self.destination = self.base/'installed'
        image = io.BytesIO()
        Image.new('RGBA', (8, 8), '#123456').save(image, format='PNG')
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode='w:gz') as archive:
            for name in ('NeoLine', 'NeoLine-White', 'NeoLine-Yellow'):
                for filename, data in (
                    ('index.theme', f'[Icon Theme]\nName={name}\nInherits=breeze-dark\nDirectories=8x8/apps\n\n[8x8/apps]\nSize=8\nType=Fixed\n'.encode()),
                    ('8x8/apps/demo.png', image.getvalue()),
                ):
                    member = tarfile.TarInfo('snapshot/'+name+'/'+filename)
                    member.size = len(data)
                    archive.addfile(member, io.BytesIO(data))
        self.body = output.getvalue()
        self.source = replace(catalog.SOURCES[3], package=replace(catalog.SOURCES[3].package,
                              size=len(self.body), sha256=hashlib.sha256(self.body).hexdigest()))
        mocked = patch.object(catalog, 'SOURCES', (self.source,))
        mocked.start()
        self.addCleanup(mocked.stop)
        self.calls = []

    def opener(self, request, *, timeout):
        self.calls.append((request.full_url, timeout))
        return Response(self.body, {'Content-Length': str(len(self.body))}, url=self.source.package.url)

    def install(self, opener=None):
        return catalog.install_source(self.source, self.destination, opener=opener or self.opener, scratch=self.scratch)

    def test_verified_archive_installs_three_real_themes_and_cleans_up(self):
        result = self.install()
        self.assertIsInstance(result, list, 'installer must return installed paths')
        self.assertEqual(sorted(p.name for p in result), ['NeoLine', 'NeoLine-White', 'NeoLine-Yellow'])
        for path in result:
            self.assertTrue(icons.validate_theme(path).samples)
        self.assertEqual(self.calls, [(self.source.package.url, 20)])
        self.assertEqual(list(self.scratch.iterdir()), [])
        self.assertEqual(online.MAX_DOWNLOAD, 64*1024*1024)
        self.assertEqual(installer.MAX_FILES, 20000)

    def test_integrity_and_size_failures_never_reach_installer(self):
        cases = [
            (self.body, {'Content-Length': 'invalid'}, self.source.package),
            (self.body, {'Content-Length': '-1'}, self.source.package),
            (self.body, {'Content-Length': '１２'}, self.source.package),
            (self.body, {'Content-Length': str(len(self.body)+1)}, self.source.package),
            (self.body, {'Content-Length': str(online.MAX_DOWNLOAD+1)}, self.source.package),
            (self.body[:-1], {}, self.source.package),
            (self.body+b'x', {}, self.source.package),
            (b'x'*len(self.body), {}, self.source.package),
            (self.body, {}, replace(self.source.package, size=online.MAX_DOWNLOAD+1)),
            (self.body, {}, replace(self.source.package, size=0)),
            (self.body, {}, replace(self.source.package, sha256='bad')),
        ]
        for body, headers, package in cases:
            with self.subTest(headers=headers, package=package):
                source = replace(self.source, package=package)
                with patch.object(catalog, 'SOURCES', (source,)), patch.object(icons, 'install') as install:
                    with self.assertRaises(ValueError):
                        catalog.install_source(source, self.destination,
                            opener=lambda *a, **kw: Response(body, headers), scratch=self.scratch)
                    install.assert_not_called()
                self.assertEqual(list(self.scratch.iterdir()), [])
                self.assertFalse(self.destination.exists())

    def test_invalid_pinned_package_is_rejected_before_network(self):
        mutations = ({'repo': 'evil/repo'}, {'repo': 'Morzilla/neoline-icons?x=1'},
                     {'commit': 'main'}, {'commit': 'a'*40+'?query'}, {'commit': 'a'*40+'#fragment'},
                     {'name': '../NeoLine.tar.gz'}, {'name': '/outside.tar.gz'})
        for mutation in mutations:
            source = replace(self.source, package=replace(self.source.package, **mutation))
            with self.subTest(mutation=mutation), patch.object(catalog, 'SOURCES', (source,)):
                opener = Mock(side_effect=AssertionError('network must not open'))
                with self.assertRaises(ValueError):
                    catalog.install_source(source, self.destination, opener=opener, scratch=self.scratch)
                opener.assert_not_called()
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_every_redirect_is_refused_before_following(self):
        from urllib.request import Request
        self.assertTrue(hasattr(catalog, 'RejectRedirect'), 'redirect denial policy missing')
        handler = catalog.RejectRedirect()
        for status in (301, 302, 303, 307, 308):
            for target in (self.source.package.url, 'https://codeload.github.com/elsewhere',
                           'https://evil.test/steal', 'http://codeload.github.com/', 'file:///etc/passwd'):
                with self.subTest(status=status, target=target):
                    with self.assertRaises(ValueError):
                        handler.redirect_request(Request(self.source.package.url), None, status, '', {}, target)
        fake = Mock()
        fake.open.side_effect = self.opener
        with patch('urllib.request.build_opener', return_value=fake) as build:
            result = catalog.install_source(self.source, self.destination, scratch=self.scratch)
        self.assertEqual(len(result), 3)
        self.assertIsInstance(build.call_args.args[0], catalog.RejectRedirect)

    def test_injected_redirect_response_is_refused(self):
        for status, url in ((302, self.source.package.url), (200, 'https://evil.test/redirected')):
            with self.subTest(status=status, url=url), patch.object(icons, 'install') as install:
                with self.assertRaises(ValueError):
                    self.install(lambda *a, **kw: Response(self.body, status=status, url=url))
                install.assert_not_called()
            self.assertEqual(list(self.scratch.iterdir()), [])

    def test_missing_length_is_safe_when_pinned_digest_and_size_match(self):
        with patch.object(icons, 'apply', side_effect=AssertionError('must not apply')):
            result = self.install(lambda *a, **kw: Response(self.body))
        self.assertEqual(len(result), 3)
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_download_exception_always_cleans_temporary_files(self):
        class Interrupted(Response):
            def read(self, size=-1):
                raise TimeoutError('offline simulated timeout')
        for opener in (Mock(side_effect=TimeoutError('offline')), lambda *a, **kw: Interrupted(self.body)):
            with self.subTest(opener=opener), self.assertRaises(TimeoutError):
                self.install(opener)
            self.assertEqual(list(self.scratch.iterdir()), [])
            self.assertFalse(self.destination.exists())

    def test_safe_installer_preserves_existing_themes(self):
        installed = self.install()
        original = {p.name: (p/'8x8/apps/demo.png').read_bytes() for p in installed}
        with self.assertRaises(FileExistsError):
            self.install()
        self.assertEqual({p.name: (p/'8x8/apps/demo.png').read_bytes() for p in installed}, original)
        self.assertEqual(sorted(p.name for p in self.destination.iterdir()), sorted(original))
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_safe_installer_retains_all_extraction_quotas(self):
        for quota in ('MAX_FILES', 'MAX_FILE', 'MAX_BYTES', 'MAX_RATIO'):
            with self.subTest(quota=quota), patch.object(installer, quota, 1):
                with self.assertRaises(ValueError):
                    self.install()
            self.assertEqual(list(self.destination.iterdir()), [])
            self.assertEqual(list(self.scratch.iterdir()), [])

    def test_publication_race_rolls_back_without_replacing(self):
        import ctypes
        from types import SimpleNamespace
        native = ctypes.CDLL(None, use_errno=True).renameat2
        native.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        competitor = []
        class Race:
            count = 0
            def __call__(self, a, source, b, target, flags):
                self.count += 1
                if self.count == 2:
                    path = Path(os.fsdecode(target))
                    path.mkdir()
                    (path/'keep').write_text('competitor')
                    competitor.append(path)
                return native(a, source, b, target, flags)
        with patch('icons.ctypes.CDLL', return_value=SimpleNamespace(renameat2=Race())):
            with self.assertRaises(FileExistsError):
                self.install()
        self.assertEqual(list(self.destination.iterdir()), competitor)
        self.assertEqual((competitor[0]/'keep').read_text(), 'competitor')
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_digest_valid_malicious_archive_is_not_installed(self):
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode='w:gz') as archive:
            member = tarfile.TarInfo('../escape')
            member.size = 1
            archive.addfile(member, io.BytesIO(b'x'))
        body = output.getvalue()
        source = replace(self.source, package=replace(self.source.package, size=len(body), sha256=hashlib.sha256(body).hexdigest()))
        with patch.object(catalog, 'SOURCES', (source,)):
            with self.assertRaises(ValueError):
                catalog.install_source(source, self.destination, opener=lambda *a, **kw: Response(body), scratch=self.scratch)
        self.assertFalse((self.base/'escape').exists())
        self.assertEqual(list(self.destination.iterdir()), [])
        self.assertEqual(list(self.scratch.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
