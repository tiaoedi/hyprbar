"""Icon theme safety and real Tk integration; all writes use scratch homes."""
from __future__ import annotations
import configparser
import hashlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
try:
    import icons
except ModuleNotFoundError:
    icons = None


def fixture(base: Path, name: str = 'Example') -> Path:
    root = base / name
    (root/'32x32/apps').mkdir(parents=True)
    (root/'index.theme').write_text('[Icon Theme]\nName=Example\nComment=Demo\nDirectories=32x32/apps\n\n[32x32/apps]\nSize=32\nType=Fixed\nContext=Applications\n')
    Image.new('RGBA', (32, 32), '#123456').save(root/'32x32/apps/demo.png')
    return root


class ScratchCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)


class Installation(ScratchCase):
    def test_local_folder_installs_without_replacing(self):
        self.assertIsNotNone(icons, 'icon theme backend missing')
        source = fixture(self.base/'input')
        destination = self.base/'installed'
        paths = icons.install(source, destination)
        self.assertEqual(paths, [destination/'Example'])
        self.assertEqual(icons.validate_theme(paths[0]).name, 'Example')
        with self.assertRaises(FileExistsError):
            icons.install(source, destination)
        self.assertEqual((paths[0]/'32x32/apps/demo.png').read_bytes(), (source/'32x32/apps/demo.png').read_bytes())

    def test_rejects_escaping_declared_directory_and_cross_theme_alias(self):
        root = fixture(self.base/'input')
        text = (root/'index.theme').read_text()
        (root/'index.theme').write_text(text.replace('32x32/apps', '../Example/32x32/apps'))
        with self.assertRaises(ValueError): icons.install(root, self.base/'installed')
        (root/'index.theme').write_text(text)
        outside = self.base/'input'/'other'; outside.mkdir()
        Image.new('RGBA', (32,32)).save(outside/'external.png')
        (root/'32x32/apps/link.png').symlink_to('../../../other/external.png')
        with self.assertRaises(ValueError): icons.install(root.parent, self.base/'installed')
        self.assertFalse((self.base/'installed'/'Example').exists())

    def test_rejects_malformed_theme_and_fake_icons(self):
        root = fixture(self.base/'input')
        for text in ('[Icon Theme]\nName=Cursor\n', '[Icon Theme]\nDirectories=/tmp\n', '[Icon Theme]\nDirectories=32x32/apps\n'):
            (root/'index.theme').write_text(text)
            with self.assertRaises(ValueError): icons.validate_theme(root)
        root = fixture(self.base/'second')
        (root/'32x32/apps/demo.png').write_bytes(b'not an image')
        with self.assertRaises(ValueError): icons.validate_theme(root)

    def test_archive_traversal_collection_atomicity_and_flat_name(self):
        import tarfile
        root = fixture(self.base/'input')
        package = self.base/'Flat.tar.gz'
        with tarfile.open(package,'w:gz') as archive:
            for p in root.iterdir(): archive.add(p,arcname=p.name)
        self.assertEqual(icons.install(package,self.base/'installed')[0].name,'Flat')
        bad = self.base/'bad.tar.gz'
        with tarfile.open(bad,'w:gz') as archive:
            member=tarfile.TarInfo('../escape'); member.size=1; archive.addfile(member,io.BytesIO(b'x'))
        with self.assertRaises(ValueError): icons.install(bad,self.base/'installed')
        collection=self.base/'collection'; fixture(collection,'A'); invalid=fixture(collection,'B')
        (invalid/'32x32/apps/demo.png').write_bytes(b'fake')
        with self.assertRaises(ValueError): icons.install(collection,self.base/'installed')
        self.assertFalse((self.base/'installed'/'A').exists())

    def test_flat_tgz_preserves_package_name(self):
        import tarfile
        root=fixture(self.base/'input'); package=self.base/'FlatIcons.tgz'
        with tarfile.open(package,'w:gz') as tar:
            for p in root.iterdir():tar.add(p,arcname=p.name)
        self.assertEqual(icons.install(package,self.base/'installed')[0].name,'FlatIcons')

    def test_publish_race_rolls_back_without_overwriting_competitor(self):
        import ctypes
        import types
        collection=self.base/'collection';fixture(collection,'A');fixture(collection,'B')
        destination=self.base/'installed'
        native=ctypes.CDLL(None,use_errno=True).renameat2
        native.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
        class Race:
            count=0
            def __call__(self,a,source,b,target,flags):
                self.count+=1
                if self.count==2:
                    competitor=Path(os.fsdecode(target));competitor.mkdir();(competitor/'keep').write_text('competitor')
                return native(a,source,b,target,flags)
        with patch('icons.ctypes.CDLL',return_value=types.SimpleNamespace(renameat2=Race())):
            with self.assertRaises(FileExistsError):icons.install(collection,destination)
        self.assertEqual([p.name for p in destination.iterdir()],['B'])
        self.assertEqual((destination/'B/keep').read_text(),'competitor')

    def test_extraction_quotas_are_reused(self):
        import installer
        root=fixture(self.base/'input')
        with patch.object(installer,'MAX_FILES',1):
            with self.assertRaisesRegex(ValueError,'Limites'):icons.install(root,self.base/'installed')
        self.assertFalse((self.base/'installed/Example').exists())


class Application(ScratchCase):
    def test_apply_icons_only_with_backups_and_symlink_preservation(self):
        self.assertTrue(hasattr(icons, 'apply'), 'explicit icon apply backend missing')
        root=fixture(self.base/'input'); theme=icons.validate_theme(root)
        home=self.base/'home'; cfg=home/'.config'; target=home/'linked-gtk.ini'; home.mkdir()
        old='[Settings]\ngtk-cursor-theme-name=KeepCursor\ngtk-cursor-theme-size=27\ngtk-font-name=Sans 11\n\n[Other]\nkey=value\n'
        target.write_text(old); (cfg/'gtk-3.0').mkdir(parents=True)
        link=cfg/'gtk-3.0/settings.ini'; link.symlink_to('../../linked-gtk.ini')
        calls=[]; value=['old-icons']
        def runner(args):
            calls.append(args)
            if args[1]=='get': return True, repr(value[0])
            import ast
            value[0]=ast.literal_eval(args[-1]); return True,''
        report=icons.apply(theme,home=home,runner=runner)
        self.assertEqual(os.readlink(link),'../../linked-gtk.ini')
        parser=configparser.ConfigParser();parser.read(target)
        self.assertEqual(parser['Settings']['gtk-icon-theme-name'],'Example')
        self.assertEqual(parser['Settings']['gtk-cursor-theme-name'],'KeepCursor')
        self.assertEqual(parser['Settings']['gtk-cursor-theme-size'],'27')
        self.assertEqual(parser['Other']['key'],'value')
        self.assertTrue(any(p.read_text()==old for p in home.rglob('*.bak-*')))
        self.assertTrue(all(c[:4]==['gsettings',c[1],'org.gnome.desktop.interface','icon-theme'] for c in calls))
        self.assertIn('VERIFICADO',report)
        self.assertIn('old-icons',next(home.rglob('snapshot.json')).read_text())

    def test_failed_gsettings_readback_rolls_back_files(self):
        self.assertTrue(hasattr(icons,'apply'),'explicit icon apply backend missing')
        theme=icons.validate_theme(fixture(self.base/'input'))
        home=self.base/'home'; config=home/'.config/gtk-3.0/settings.ini';config.parent.mkdir(parents=True)
        old='[Settings]\ngtk-icon-theme-name=Original\n';config.write_text(old)
        calls=[]
        def runner(args): calls.append(args);return True,"'Original'"
        with self.assertRaisesRegex(RuntimeError,'verifica'):
            icons.apply(theme,home=home,runner=runner)
        self.assertEqual(config.read_text(),old)
        self.assertFalse((home/'.config/gtk-4.0/settings.ini').exists())
        self.assertEqual(calls[-2][-1],"'Original'")
        self.assertEqual(calls[-1][1],'get','rollback must read back GSettings')


class Downloads(ScratchCase):
    def test_secure_download_routes_to_icon_installer_and_checks_digest(self):
        self.assertTrue(hasattr(icons,'install_asset'),'icon release downloader missing')
        import online,tarfile
        root=fixture(self.base/'input');out=io.BytesIO()
        with tarfile.open(fileobj=out,mode='w:gz') as tar: tar.add(root,arcname=root.name)
        body=out.getvalue(); asset=online.Asset('owner/repo','v1','icons.tar.gz',len(body),'https://github.com/owner/repo/releases/download/v1/icons.tar.gz','sha256:'+hashlib.sha256(body).hexdigest())
        class Response(io.BytesIO): headers={}
        paths=icons.install_asset(asset,self.base/'installed',opener=lambda *a,**kw:Response(body),scratch=self.base)
        self.assertEqual(paths,[self.base/'installed/Example'])
        bad=online.Asset(asset.repo,asset.version,asset.name,asset.size,asset.url,'sha256:'+'0'*64)
        with self.assertRaisesRegex(ValueError,'SHA256'):
            icons.install_asset(bad,self.base/'bad',opener=lambda *a,**kw:Response(body),scratch=self.base)
        self.assertFalse((self.base/'bad').exists())
        self.assertFalse(list(self.base.glob('icon-download-*')))

    def test_discovery_and_real_png_svg_preview_do_not_apply(self):
        self.assertTrue(hasattr(icons,'discover'),'icon discovery missing')
        root=fixture(self.base/'installed')
        themes=icons.discover([root.parent])
        self.assertEqual([t.name for t in themes],['Example'])
        self.assertEqual(icons.preview(themes[0].samples[0]).size,(96,96))
        svg=root/'32x32/apps/real.svg'
        svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><rect width="32" height="32" fill="#ff0000"/></svg>')
        image=icons.preview(svg)
        self.assertEqual(image.size,(96,96));self.assertEqual(image.getpixel((48,48))[:3],(255,0,0))
        svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"><image href="file:///etc/passwd"/></svg>')
        with self.assertRaises(ValueError):icons.preview(svg)


@unittest.skipUnless(os.environ.get('DISPLAY'), 'GUI requires DISPLAY')
class IconGui(ScratchCase):
    def setUp(self):
        super().setUp()
        import tkinter as tk
        import app
        self.enterContext(patch.dict(os.environ, {'HOME':str(self.base/'home'), 'XDG_DATA_HOME':str(self.base/'data'), 'XDG_CONFIG_HOME':str(self.base/'home/.config'), 'XDG_DATA_DIRS':str(self.base/'empty')}))
        self.enterContext(patch('app.cm.discover',return_value=[]))
        self.enterContext(patch('app.App.refresh_palette'))
        self.cursor_apply=self.enterContext(patch('app.settings.apply',side_effect=AssertionError('cursor mutation forbidden')))
        self.root=tk.Tk(); self.root.withdraw();self.addCleanup(self.cleanup_root)
        self.app=app.App(self.root)
        self.pump(lambda:self.app.status.get().startswith('0 temas'))

    def cleanup_root(self):
        for identifier in self.root.tk.call('after','info'):self.root.after_cancel(identifier)
        self.root.destroy()

    def pump(self,predicate):
        import time
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            self.root.update()
            if predicate():return
            time.sleep(.01)
        self.fail('Tk worker queue timed out')

    def test_installed_preview_local_install_and_explicit_confirmed_apply(self):
        self.assertTrue(hasattr(self.app,'icon_button'),'main icon button missing')
        installed=fixture(self.base/'data/icons','Existing')
        with patch('online.latest',side_effect=AssertionError('startup network forbidden')):
            self.app.icon_button.invoke();dialog=self.app.icon_dialog
            self.pump(lambda:len(dialog.themes)==1)
        self.assertEqual(dialog.tree.selection(),())
        dialog.tree.selection_set('Existing');self.root.update()
        self.pump(lambda:bool(dialog.images))
        self.assertIn(str(installed),dialog.detail.get())
        source=fixture(self.base/'incoming','NewIcons')
        with patch('icon_dialog.filedialog.askdirectory',return_value=str(source)),patch('icon_dialog.messagebox.askyesno',return_value=True):
            dialog.pick_install(True)
            self.pump(lambda:len(dialog.themes)==2 and not self.app.busy)
        self.assertEqual(dialog.selected.name,'NewIcons')
        self.assertFalse((self.base/'home/.config/gtk-3.0/settings.ini').exists())
        real_apply=icons.apply;value=['old']
        def runner(args):
            import ast
            if args[1]=='get':return True,repr(value[0])
            value[0]=ast.literal_eval(args[-1]);return True,''
        with patch('icon_dialog.icons.apply',side_effect=lambda t:real_apply(t,home=self.base/'home',runner=runner)) as apply,patch('icon_dialog.messagebox.askyesno',return_value=False) as confirm:
            dialog.apply_selected();apply.assert_not_called()
            confirm.return_value=True;dialog.apply_selected();self.pump(lambda:not self.app.busy)
            apply.assert_called_once()
        self.assertEqual(value[0],'NewIcons');self.assertIn('VERIFICADO',dialog.status.get())
        self.cursor_apply.assert_not_called()

    def test_external_catalogs_only_open_on_explicit_click(self):
        with patch('webbrowser.open',return_value=True) as browser,patch('online.latest') as latest:
            self.app.open_online();dialog=self.app.online_dialog
            self.assertTrue(hasattr(dialog,'flaticon_button'),'Flaticon external source missing')
            browser.assert_not_called();latest.assert_not_called()
            dialog.flaticon_button.invoke();dialog.custom_cursor_button.invoke()
            self.assertEqual([c.args[0] for c in browser.call_args_list],['https://www.flaticon.com/br/icones-gratis/cursor','https://custom-cursor.com/es/top-downloaded-cursors'])
            self.assertIn(str(len(__import__('online').FAMILIES)),dialog.status.get())
        self.cursor_apply.assert_not_called()

    def test_online_icons_install_via_real_queue_without_cursor_or_auto_apply(self):
        import online,tarfile
        self.assertTrue(hasattr(self.app,'open_icons'),'icon dialog missing')
        source=fixture(self.base/'incoming','Downloaded');buffer=io.BytesIO()
        with tarfile.open(fileobj=buffer,mode='w:gz') as tar:tar.add(source,arcname=source.name)
        body=buffer.getvalue();repo=next(iter(icons.FAMILIES.values()))
        asset=online.Asset(repo,'v1','icons.tar.gz',len(body),f'https://github.com/{repo}/releases/download/v1/icons.tar.gz')
        class Response(io.BytesIO):headers={}
        with patch('online.latest',return_value=[asset]) as latest,patch('online.open_safe',side_effect=lambda *a:Response(body)),patch('online_dialog.messagebox.askyesno',return_value=True),patch('icons.apply') as apply:
            self.app.open_icons();owner=self.app.icon_dialog;owner.open_online();dialog=owner.online_dialog
            latest.assert_not_called()
            self.assertEqual(dialog.family.get(),'Todos os repositórios')
            self.assertEqual(len(dialog.families),3)
            dialog.family.set(next(iter(icons.FAMILIES)));dialog.select_family();dialog.fetch()
            self.pump(lambda:not self.app.busy)
            self.assertEqual(len(dialog.assets),1)
            dialog.tree.selection_set('0');self.root.update();dialog.install_selected()
            self.pump(lambda:not self.app.busy and owner.selected is not None)
            self.assertEqual(owner.selected.name,'Downloaded')
            self.assertTrue((self.base/'data/icons/Downloaded/index.theme').is_file())
            self.assertIn('Nada foi aplicado',owner.status.get())
            apply.assert_not_called();self.cursor_apply.assert_not_called()

    def test_cross_dialog_busy_and_smoke_guards(self):
        self.assertTrue(hasattr(self.app,'open_icons'),'icon dialog missing')
        import threading
        fixture(self.base/'data/icons')
        self.app.open_icons();dialog=self.app.icon_dialog
        self.pump(lambda:bool(dialog.themes))
        self.app.open_online();online_dialog=self.app.online_dialog
        dialog.tree.selection_set('Example');self.root.update()
        gate=threading.Event();self.addCleanup(gate.set)
        self.app.operation(lambda:gate.wait(4),lambda *_:None)
        self.assertTrue(dialog.apply_button.instate(['disabled']))
        self.assertTrue(online_dialog.fetch_button.instate(['disabled']))
        with patch('icon_dialog.messagebox.askyesno') as confirm,patch('icons.apply') as apply,patch('icons.install_asset') as download:
            dialog.apply_selected();dialog.pick_install(True);dialog.open_online();dialog.close()
            confirm.assert_not_called();apply.assert_not_called();download.assert_not_called()
            self.assertTrue(dialog.window.winfo_exists())
            gate.set();self.pump(lambda:not self.app.busy)
            self.app.smoke=True
            dialog.apply_selected();dialog.pick_install(True)
            online_dialog.install_selected();dialog.open_online()
            confirm.assert_not_called();apply.assert_not_called();download.assert_not_called()
        self.assertTrue(hasattr(self.app,'hyprland_button'))


if __name__ == '__main__':
    unittest.main()
