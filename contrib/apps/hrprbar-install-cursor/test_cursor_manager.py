import unittest
import tempfile
import os
from pathlib import Path
import cursor_manager as cm
import struct

# Synthetic test input, independent of the user's installed themes.
SCRATCH = Path(os.environ.get('TMPDIR', Path.home()/'.cache'/'hrprbar-install-cursor'/'tests'))
SCRATCH.mkdir(parents=True, exist_ok=True)
os.environ['TMPDIR'] = str(SCRATCH)

def fixture_cursor() -> bytes:
    frames=[]
    for size in (24,32,48):
        pixels=[0xff000000 if x<=y//2 and y<size-3 else 0 for y in range(size) for x in range(size)]
        frames.append(struct.pack('<9I',36,0xfffd0002,size,1,size,size,1,1,0)+struct.pack('<'+str(len(pixels))+'I',*pixels))
    offset=16+12*len(frames);toc=[]
    for size,frame in zip((24,32,48),frames):
        toc.append(struct.pack('<III',0xfffd0002,size,offset));offset+=len(frame)
    return struct.pack('<4I',0x72756358,16,0x10000,len(frames))+b''.join(toc)+b''.join(frames)

class DiscoveryTests(unittest.TestCase):
    def test_user_precedence_and_ignore_icons(self):
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as tmp:
            a, b = Path(tmp)/'user', Path(tmp)/'system'
            for root in (a,b):
                (root/'Tema'/'cursors').mkdir(parents=True)
                (root/'Tema'/'cursors'/'left_ptr').write_bytes(b'Xcur')
            (a/'Icones').mkdir()
            themes=cm.discover([a,b])
            self.assertEqual(len(themes),1)
            self.assertEqual(themes[0].path,a/'Tema')

class PreviewTests(unittest.TestCase):
    def test_actual_image(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            path=Path(tmp)/'left_ptr';path.write_bytes(fixture_cursor())
            image, nominal, sizes = cm.preview(path,40)
            self.assertEqual(nominal,32)
            self.assertIn(32,sizes)
            self.assertGreater(image.getbbox()[2],0)

class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ['TMPDIR'])
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
    def test_folder_internal_alias_and_no_overwrite(self):
        import shutil
        source=self.root/'Tema'; (source/'cursors').mkdir(parents=True)
        (source/'cursors'/'left_ptr').write_bytes(fixture_cursor())
        (source/'cursors'/'default').symlink_to('left_ptr')
        installed=cm.install(source,self.root/'icons')
        self.assertEqual([p.name for p in installed],['Tema'])
        self.assertTrue((installed[0]/'cursors'/'default').is_file())
        with self.assertRaises(FileExistsError): cm.install(source,self.root/'icons')
    def test_reject_bad_archives(self):
        import tarfile,io,zipfile
        for name in ('../escape','/escape'):
            p=self.root/'bad.zip'
            with zipfile.ZipFile(p,'w') as z: z.writestr(name,b'x')
            with self.assertRaises(ValueError): cm.install(p,self.root/'icons')
        for kind in (tarfile.SYMTYPE,tarfile.LNKTYPE,tarfile.CHRTYPE):
            p=self.root/'bad.tar'
            with tarfile.open(p,'w') as t:
                m=tarfile.TarInfo('Tema/cursors/evil');m.type=kind;m.linkname='../../outside';t.addfile(m)
            with self.assertRaises(ValueError): cm.install(p,self.root/'icons')
    def test_archive_theme_roots_and_flat_package_name(self):
        import zipfile
        data=fixture_cursor()
        p=self.root/'Colecao.zip'
        with zipfile.ZipFile(p,'w') as z:
            z.writestr('repo/TemaA/cursors/left_ptr',data)
            z.writestr('repo/TemaB/cursors/left_ptr',data)
        installed=cm.install(p,self.root/'icons')
        self.assertEqual(sorted(x.name for x in installed),['TemaA','TemaB'])
        p=self.root/'TemaPlano.zip'
        with zipfile.ZipFile(p,'w') as z:z.writestr('cursors/left_ptr',data)
        installed=cm.install(p,self.root/'icons')
        self.assertEqual([x.name for x in installed],['TemaPlano'])

    def test_quotas(self):
        import zipfile
        p=self.root/'big.zip'
        with zipfile.ZipFile(p,'w',compression=zipfile.ZIP_DEFLATED) as z: z.writestr('Tema/cursors/big',b'0'*2000000)
        with self.assertRaises(ValueError): cm.install(p,self.root/'icons')

class SettingsTests(unittest.TestCase):
    def test_plan_and_apply_isolated(self):
        import settings
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as tmp:
            home=Path(tmp); real=home/'dotfiles'/'hyprland.lua';real.parent.mkdir()
            text='hl.env("XCURSOR_THEME", "old")\nhl.env("XCURSOR_SIZE", "24")\nhl.env("HYPRCURSOR_THEME", "old")\nhl.env("HYPRCURSOR_SIZE", "24")\nhl.config({cursor={no_hardware_cursors=1,enable_hyprcursor=true},general={gaps_in=3}})\n'
            real.write_text(text)
            config=home/'.config'/'hypr';config.mkdir(parents=True);(config/'hyprland.lua').symlink_to(real)
            gtk=home/'.config'/'gtk-3.0';gtk.mkdir();(gtk/'settings.ini').write_text('[Settings]\ngtk-theme-name=Keep\n')
            (home/'.Xresources').write_text('Other.value: keep\n')
            theme=cm.Theme('Novo',home,True,False)
            report=settings.persist(theme,32,home)
            self.assertIn('no_hardware_cursors=1',real.read_text())
            self.assertIn('enable_hyprcursor=false',real.read_text())
            self.assertIn('gtk-theme-name = Keep',(gtk/'settings.ini').read_text())
            self.assertIn('Other.value: keep',(home/'.Xresources').read_text())
            self.assertEqual(len(report),4)
            self.assertEqual(next(real.parent.glob('*.bak-*')).read_text(),text)
            settings.persist(theme,32,home)
            self.assertEqual((home/'.Xresources').read_text().count('BEGIN hrprbar-install cursor'),1)
    def test_exact_sizes(self):
        import settings
        self.assertEqual(settings.snap_size(40,[24,32,48]),32)
        self.assertEqual(settings.snap_size(47,[24,32,48]),48)
    def test_runtime_readback_disagreement_reported(self):
        import settings
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as tmp:
            home=Path(tmp);config=home/'.config/hypr';config.mkdir(parents=True)
            (config/'hyprland.lua').write_text('hl.config({cursor={enable_hyprcursor=true}})\n')
            def fixture_runner(argv,data=None):
                if argv[:2]==['gsettings','get']:return True,"'Outro'" if argv[-1]=='cursor-theme' else '24'
                if argv==['xrdb','-query']:return True,'Xcursor.theme: Outro\nXcursor.size: 24'
                if argv[:3]==['systemctl','--user','show-environment']:return True,'XCURSOR_THEME=Outro\nXCURSOR_SIZE=24'
                if argv[:2]==['hyprctl','getoption']:return True,'{"int":1}'
                if argv[:2]==['hyprctl','monitors']:return True,'[{"name":"Teste","scale":1.5}]'
                return True,''
            report=settings.apply(cm.Theme('Novo',home,True,False),32,home=home,runner=fixture_runner,inspect_apps=False)
            for label in ('GSettings tema','GSettings tamanho','Xresources runtime','systemd ambiente','Hyprland modo Xcursor'):
                self.assertIn('NÃO CONFIRMADO '+label,report)
            self.assertIn('Teste escala 1.5',report)

    def test_runtime_bool_api_is_verified(self):
        import settings
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as tmp:
            home=Path(tmp); config=home/'.config/hypr'; config.mkdir(parents=True)
            (config/'hyprland.lua').write_text('hl.config({cursor={enable_hyprcursor=true}})\n')
            def fixture_runner(argv,data=None):
                if argv[:2]==['hyprctl','getoption']: return True,'{"bool":false,"set":true}'
                if argv[:2]==['hyprctl','monitors']: return True,'[]'
                return True,''
            report=settings.apply(cm.Theme('Novo',home,True,False),32,home=home,runner=fixture_runner,inspect_apps=False)
            self.assertIn('VERIFICADO Hyprland modo Xcursor:',report)

    def test_verification_rejects_disagreement(self):
        import settings
        self.assertFalse(settings.matches('wrong','32','Novo',32))
        self.assertTrue(settings.matches('Novo','32','Novo',32))

class LauncherTests(unittest.TestCase):
    def test_run_list(self):
        import subprocess,sys,json
        proc=subprocess.run(['sh',str(Path(__file__).parent/'run.sh'),'--list'],env={**os.environ,'PYTHON':sys.executable},capture_output=True,text=True,timeout=30)
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertIsInstance(json.loads(proc.stdout),list)

class GuiTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('DISPLAY'), 'GUI requires an active X11/XWayland display')
    def test_smoke_readonly(self):
        import subprocess,sys,json
        proc=subprocess.run([sys.executable,str(Path(__file__).parent/'app.py'),'--smoke-test'],capture_output=True,text=True,timeout=30)
        self.assertEqual(proc.returncode,0,proc.stderr)
        result=json.loads(proc.stdout)
        self.assertEqual(result['title'],'hrprbar-install cursor')
        self.assertGreater(result['rendered'],0)
        self.assertFalse(result['applied'])
        self.assertGreater(result['widgets'],25)
        self.assertEqual(result['heading_font_size'],19)

class PaletteTests(unittest.TestCase):
    def test_dark_light_and_missing_palette(self):
        import palette,json
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as tmp:
            base=Path(tmp)
            (base/'Rose%20Pine%20Alt.json').write_text(json.dumps({'dark':{'mSurface':'#191724','mPrimary':'#c4a7e7'},'light':{'mSurface':'#fffaf3','mPrimary':'#907aa9'}}))
            dark=palette.resolve('community Rose Pine Alt','dark',base)
            light=palette.resolve('community Rose Pine Alt','light',base)
            self.assertEqual(dark['colors']['mSurface'],'#191724')
            self.assertEqual(light['colors']['mSurface'],'#fffaf3')
            self.assertEqual(dark['name'],'Rose Pine Alt')
            self.assertTrue(palette.resolve('community missing','dark',base)['fallback'])

if __name__ == '__main__': unittest.main()
