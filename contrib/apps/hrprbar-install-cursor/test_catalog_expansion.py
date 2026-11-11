"""Offline regressions for release sources verified against GitHub's API.

Verified 2026-11-11 using /repos/{repo}/releases/latest; downloaded one
published Linux archive per source and checked Xcursor magic in cursors/.
No network requests or desktop changes are made by these tests.
"""
import io
import json
import unittest
from unittest.mock import patch

import online


# Actual published release metadata, not GitHub's source-only tarball URLs.
VERIFIED_RELEASES = {
    'ful1e5/banana-cursor': ('v2.0.0', 'Banana.tar.xz', 3575776),
    'ful1e5/notwaita-cursor': ('v1.0.0-alpha1', 'Notwaita-White.tar.xz', 1791332),
    'phisch/phinger-cursors': ('v2.2', 'phinger-cursors-variants.tar.bz2', 1922305),
    'rose-pine/cursors': ('v1.1.0', 'BreezeX-RosePine-Linux.tar.xz', 864184),
}


class ExpandedCatalogTests(unittest.TestCase):
    def test_default_catalog_includes_verified_extra_sources_without_duplicates(self):
        original = {
            'Bibata': 'ful1e5/Bibata_Cursor',
            'BreezeX': 'ful1e5/BreezeX_Cursor',
            'GoogleDot': 'ful1e5/Google_Cursor',
            'macOS': 'ful1e5/apple_cursor',
            'Fuchsia': 'ful1e5/fuchsia-cursor',
        }
        self.assertLessEqual(set(VERIFIED_RELEASES), set(online.FAMILIES.values()))
        self.assertEqual({key: online.FAMILIES[key] for key in original}, original)
        self.assertEqual(len(online.FAMILIES), len(set(r.casefold() for r in online.FAMILIES.values())))
        calls = []

        def release(repo):
            calls.append(repo)
            return [online.Asset(repo, 'v1', 'Linux.tar.xz', 100,
                                 f'https://github.com/{repo}/releases/download/v1/Linux.tar.xz')]

        with patch('online.latest', side_effect=release):
            result = online.catalog()
        self.assertCountEqual(calls, online.FAMILIES.values())
        self.assertEqual({asset.repo for asset in result.assets}, set(online.FAMILIES.values()))
        self.assertEqual(set(result.statuses), set(online.FAMILIES.values()))

    def test_verified_linux_packages_pass_existing_release_validation(self):
        for repo, (version, name, size) in VERIFIED_RELEASES.items():
            with self.subTest(repo=repo):
                url = f'https://github.com/{repo}/releases/download/{version}/{name}'
                body = {'tag_name': version, 'assets': [
                    {'name': name, 'size': size, 'browser_download_url': url},
                    {'name': 'Windows.zip', 'size': 123, 'browser_download_url': 'https://example.invalid/Windows.zip'},
                ]}
                calls = []

                def response(request, timeout):
                    calls.append(request.full_url)
                    return io.BytesIO(json.dumps(body).encode())

                assets = online.latest(repo, opener=response)
                self.assertEqual(assets, [online.Asset(repo, version, name, size, url)])
                self.assertEqual(calls, [f'https://api.github.com/repos/{repo}/releases/latest'])


if __name__ == '__main__':
    unittest.main()
