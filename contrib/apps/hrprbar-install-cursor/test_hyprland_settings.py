"""Isolated fixtures only: never save/reload the real desktop."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
import importlib

class OptionTests(unittest.TestCase):
    def test_scalar_validation_and_lua_escaping(self):
        m=importlib.import_module('hyprland_settings')
        option=m.Option({'name':'general:border_size','current':1,'default':1,'min':0,'max':20})
        self.assertEqual(option.parse('3'),3)
        for bad in ('1.5','-1','21','nan'):
            with self.assertRaises(ValueError):option.parse(bad)
        self.assertEqual(m.lua_value('a"\n\\'), '"a\\"\\n\\\\"')
        self.assertEqual(m.lua_value(True),'true')
        self.assertFalse(m.Option({'name':'debug:manual_crash','current':0}).editable)
        self.assertFalse(m.Option({'name':'input:vector','current':[0,0]}).editable)

    def test_color_vector_and_name_validation(self):
        import hyprland_settings as m
        for raw in ({'name':'general:col.active_border','current':'88ffffff 0deg'}, {'name':'decoration:blur:aurora:color1','current':'29f0a0ff'}, {'name':'input:vector','current':[0,0]}, {'name':'general:gaps_in','current':'2 2 2 2'}):
            self.assertFalse(m.Option(raw).editable)
        self.assertIn(b'["general.col.active_border"]',m.managed_config(b'-- base\n',{'general:col.active_border':'0xff000000'}))

    def test_boolean_float_and_strings_validate(self):
        import hyprland_settings as m
        self.assertFalse(m.Option({'name':'input:bool','current':True}).parse('false'))
        with self.assertRaises(ValueError):m.Option({'name':'input:bool','current':True}).parse('yes')
        for invalid in ('nan','inf','-inf'):
            with self.assertRaises(ValueError):m.Option({'name':'input:sensitivity','current':0.0}).parse(invalid)
        self.assertEqual(m.Option({'name':'input:kb_layout','current':'us'}).parse('br'),'br')

class PersistenceTests(unittest.TestCase):
    def test_managed_block_merge_strict_markers_and_symlink_save(self):
        import hyprland_settings as m
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'real.lua';target.write_bytes(b'-- original\nhl.config({})\n');target.chmod(0o640)
            link=Path(td)/'hyprland.lua';link.symlink_to(target)
            doc=m.Document(link)
            first=m.managed_config(doc.original, {'general:border_size':3})
            second=m.managed_config(first, {'input:follow_mouse':True})
            self.assertIn(b'["general.border_size"] = 3',second)
            self.assertIn(b'["input.follow_mouse"] = true',second)
            self.assertEqual(second.count(m.BEGIN.encode()),1)
            backup=doc.save(second)
            self.assertTrue(link.is_symlink());self.assertEqual(backup.read_bytes(),b'-- original\nhl.config({})\n')
            self.assertEqual(target.stat().st_mode & 0o777,0o640)
            self.assertEqual(target.read_bytes(),second)
            with self.assertRaises(ValueError):m.managed_config(b'-- hrprbar-settings:begin\n',{})
            with self.assertRaises(ValueError):m.managed_config(second+b'print(1)\n',{})

    def test_readback_failure_restores_original_from_backup(self):
        import hyprland_settings as m
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'hyprland.lua';target.write_bytes(b'-- original\n')
            doc=m.Document(target)
            real_read=Path.read_bytes
            corrupted=[False]
            def read(path):
                value=real_read(path)
                if path==target and value==b'-- new\n' and not corrupted[0]:
                    corrupted[0]=True;return b'corrupt'
                return value
            with patch.object(Path,'read_bytes',read):
                with self.assertRaises(OSError):doc.save(b'-- new\n')
            self.assertEqual(target.read_bytes(),b'-- original\n')

    def test_invalid_syntax_concurrent_edits_and_write_failure_leave_original(self):
        import hyprland_settings as m
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'hyprland.lua';target.write_bytes(b'-- original\n')
            doc=m.Document(target)
            with self.assertRaises(RuntimeError):doc.save(b'hl.config({ invalid lua\n')
            self.assertEqual(target.read_bytes(),b'-- original\n')
            target.write_bytes(b'-- concurrent\n')
            with self.assertRaises(ValueError):doc.save(b'-- new\n')
            self.assertEqual(target.read_bytes(),b'-- concurrent\n')
            doc=m.Document(target)
            with patch.object(m.os,'replace',side_effect=OSError('fixture disk full')):
                with self.assertRaises(OSError):doc.save(b'-- new\n')
            self.assertEqual(target.read_bytes(),b'-- concurrent\n')
            self.assertFalse(list(Path(td).glob('.hyprland.lua.*')))

    def test_managed_block_rejects_tampering_and_dangerous_names(self):
        import hyprland_settings as m
        valid=m.managed_config(b'-- base\n',{'general:border_size':3})
        for data in (valid+valid,valid.replace(b'= 3',b'= 4'),b'-- hrprbar-settings:end\n-- hrprbar-settings:begin\n',valid.replace(b'-- valores: {',b'-- valores: broken{')):
            with self.assertRaises(ValueError):m.managed_config(data,{})
        for name in ('debug:manual_crash','debug.manual_crash','bad"name'):
            with self.assertRaises(ValueError):m.managed_config(b'-- base\n',{name:1})

    def test_symlink_retarget_and_backup_failure_refuse_write(self):
        import hyprland_settings as m
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'real.lua';target.write_bytes(b'-- original\n')
            other=Path(td)/'other.lua';other.write_bytes(b'-- other\n')
            link=Path(td)/'hyprland.lua';link.symlink_to(target)
            doc=m.Document(link)
            link.unlink();link.symlink_to(other)
            with self.assertRaises(ValueError):doc.save(b'-- new\n')
            self.assertEqual(target.read_bytes(),b'-- original\n');self.assertEqual(other.read_bytes(),b'-- other\n')
            doc=m.Document(link)
            real_open=m.os.open
            def open_file(path,*args,**kwargs):
                if '.backup-' in str(path):raise PermissionError('fixture backup denied')
                return real_open(path,*args,**kwargs)
            with patch.object(m.os,'open',side_effect=open_file):
                with self.assertRaises(PermissionError):doc.save(b'-- new\n')
            self.assertEqual(other.read_bytes(),b'-- other\n')

    def test_syntax_validation_never_executes_lua_and_runner_is_injectable(self):
        import hyprland_settings as m
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'hyprland.lua';target.write_bytes(b'-- original\n')
            marker=Path(td)/'must-not-exist'
            m.Document(target).validate(('os.execute("touch '+str(marker)+'")\n').encode())
            self.assertFalse(marker.exists())
            commands=[]
            def runner(args):
                commands.append(args[:2]);raise RuntimeError('fixture syntax failure')
            with self.assertRaises(RuntimeError):m.Document(target,runner=runner).save(b'-- new\n')
            self.assertEqual(commands,[['luac','-p']]);self.assertEqual(target.read_bytes(),b'-- original\n')

class RuntimeTests(unittest.TestCase):
    def test_runtime_discovers_matching_socket_proc_binary_and_config(self):
        import hyprland_settings as m
        with tempfile.TemporaryDirectory() as td:
            proc=Path(td)/'proc';pid=proc/'42';pid.mkdir(parents=True)
            binary=Path(td)/'Hyprland';binary.touch();(pid/'exe').symlink_to(binary)
            cfg=Path(td)/'active.lua';cfg.write_text('hl.config({})\n')
            (pid/'cmdline').write_bytes(b'Hyprland\0--config\0'+os.fsencode(cfg)+b'\0')
            (pid/'environ').write_bytes(b'HOME=/fixture\0')
            calls=[]
            def runner(args):
                calls.append(args)
                if args==['hyprctl','instances','-j']:
                    return '[{"instance":"other","wl_socket":"wayland-2","pid":9},{"instance":"active","wl_socket":"wayland-1","pid":42}]'
                if 'descriptions' in args:return '[{"name":"general:border_size","current":1}]'
                if 'getoption' in args:return '{"bool":false}'
                return ''
            r=m.Runtime(runner,proc,{'WAYLAND_DISPLAY':'wayland-1','HYPRLAND_INSTANCE_SIGNATURE':'stale'})
            self.assertEqual(r.binary,binary);self.assertEqual(r.config,cfg)
            self.assertEqual(len(r.options()),1)
            self.assertIn(['hyprctl','-i','active','descriptions','-j'],calls)
            with self.assertRaises(ValueError):r.ensure_save_safe()
            with self.assertRaises(ValueError):m.Runtime(runner,proc,{'WAYLAND_DISPLAY':'unknown'})

    def test_runner_uses_timeout_no_shell_and_reports_command_failure(self):
        import hyprland_settings as m
        from unittest.mock import patch
        result=subprocess.CompletedProcess(['fixture'],1,stdout='',stderr='fixture error')
        with patch.object(m.subprocess,'run',return_value=result) as call:
            with self.assertRaisesRegex(RuntimeError,'fixture error'):m.run(['fixture','space argument'])
            self.assertEqual(call.call_args.args[0],['fixture','space argument'])
            self.assertEqual(call.call_args.kwargs['timeout'],15)
            self.assertNotIn('shell',call.call_args.kwargs)
        with patch.object(m.subprocess,'run',side_effect=subprocess.TimeoutExpired(['fixture'],15)):
            with self.assertRaises(subprocess.TimeoutExpired):m.run(['fixture'])

    def test_runtime_schema_readback_reload_errors_and_autoreload_guard(self):
        import hyprland_settings as m
        r=m.Runtime.__new__(m.Runtime);r.instance={'instance':'fixture'}
        replies={'descriptions':'[{"name":"general:border_size","current":1}]','getoption':'{"bool":true}','reload':'ok','configerrors':''}
        commands=[]
        def runner(args):commands.append(args);return replies[args[3]]
        r.runner=runner
        self.assertEqual(len(r.options()),1)
        r.ensure_save_safe()
        self.assertEqual(r.readback(['misc:disable_autoreload']),{'misc:disable_autoreload':{'bool':True}})
        self.assertNotIn('reload',[args[3] for args in commands])
        self.assertEqual(r.reload(),'ok')
        replies['configerrors']='fixture config error'
        with self.assertRaisesRegex(RuntimeError,'fixture config error'):r.reload()
        for value in ('{}','{"bool":false,"int":1}','{"int":0}'):
            replies['getoption']=value
            with self.assertRaises(ValueError):r.ensure_save_safe()
        replies['getoption']='{"int":1}';r.ensure_save_safe()
        for value in ('[]','{}','[{"name":"same"},{"name":"same"}]','bad json'):
            replies['descriptions']=value
            with self.assertRaises(ValueError):r.options()

    def test_explicit_prepare_save_disables_only_autoreload_and_verifies(self):
        import hyprland_settings as m
        r=m.Runtime.__new__(m.Runtime);r.instance={'instance':'fixture'}
        commands=[]
        def runner(args):
            commands.append(args)
            return 'ok' if args[3]=='eval' else '{"bool":true}'
        r.runner=runner;r.disable_autoreload()
        self.assertEqual(commands,[['hyprctl','-i','fixture','eval','hl.config({["misc.disable_autoreload"] = true})'],['hyprctl','-i','fixture','getoption','misc:disable_autoreload','-j']])
        r.runner=lambda args:'ok' if args[3]=='eval' else '{"bool":false}'
        with self.assertRaises(ValueError):r.disable_autoreload()

class DialogTests(unittest.TestCase):
    def test_real_tk_worker_filters_stages_cancels_and_smoke_blocks(self):
        import tkinter as tk
        import queue
        import threading
        import time
        from unittest.mock import patch
        import hyprland_settings as m
        import hyprland_dialog as ui
        root=tk.Tk();root.withdraw()
        class App:
            smoke=False;busy=False; font_family='Liberation Sans'
            def __init__(self):self.root=root;self.queue=queue.Queue()
            def operation(self,fn,done):
                def worker():
                    try:self.queue.put((done,fn(),None))
                    except Exception as exc:self.queue.put((done,None,exc))
                threading.Thread(target=worker,daemon=True).start()
        with tempfile.TemporaryDirectory() as td:
            cfg=Path(td)/'hyprland.lua';cfg.write_text('hl.config({})\n')
            class Runtime:
                config=cfg;binary=Path('/fixture/Hyprland');instance={'instance':'fixture'}
                def options(self):return [m.Option({'name':'general:border_size','current':1,'default':1,'min':0,'max':20}),m.Option({'name':'input:follow_mouse','current':True,'default':False})]
                def ensure_save_safe(self):pass
                def disable_autoreload(self):self.prepared=True
                def readback(self,names):return {name:{'int':1} for name in names}
                def reload(self):raise AssertionError('Must not reload')
            app=App();dialog=ui.HyprlandDialog(app,runtime_factory=Runtime)
            def pump():
                end=time.monotonic()+3
                while time.monotonic()<end:
                    root.update()
                    try:
                        while True:
                            done,result,error=app.queue.get_nowait();done(result,error)
                    except queue.Empty:pass
                    if dialog.document is not None and not dialog.busy:return
                    time.sleep(.01)
                self.fail('queue timeout')
            pump()
            self.assertEqual(len(dialog.tree.get_children()),2)
            dialog.controls(True)
            self.assertEqual(str(dialog.apply_button['state']),'disabled')
            self.assertEqual(str(dialog.code['state']),'disabled')
            dialog.controls(False)
            self.assertEqual(str(dialog.code['state']),'normal')
            dialog.category.set('general');root.update();self.assertEqual(len(dialog.tree.get_children()),1)
            dialog.search.set('absent');root.update();self.assertEqual(len(dialog.tree.get_children()),0)
            self.assertIsNone(dialog.selected)
            dialog.search.set('');dialog.tree.selection_set('general:border_size');dialog.choose();dialog.value.set('3');dialog.stage()
            self.assertEqual(dialog.staged,{'general:border_size':3})
            with patch.object(dialog,'confirm_diff',return_value=False):dialog.save()
            self.assertEqual(cfg.read_text(),'hl.config({})\n')
            app.smoke=True
            with patch.object(dialog,'confirm_diff',side_effect=AssertionError('no confirmation in smoke')):
                dialog.save();dialog.reload();dialog.prepare_save()
            self.assertIn('smoke',dialog.status.get().lower())
            self.assertEqual(cfg.read_text(),'hl.config({})\n')
            app.smoke=False
            with patch.object(ui.messagebox,'askyesno',return_value=False):dialog.reload();dialog.prepare_save()
            self.assertEqual(dialog.apply_button['text'],'Aplicar e recarregar')
            self.assertFalse(dialog.busy)
            self.assertFalse(hasattr(dialog.runtime,'prepared'))
            with patch.object(ui.messagebox,'askyesno',return_value=True):dialog.prepare_save()
            pump();self.assertTrue(dialog.runtime.prepared)
            self.assertIn('desativada e verificada',dialog.status.get())
            root.after(40,lambda:[child.destroy() for child in dialog.window.winfo_children() if isinstance(child,tk.Toplevel)])
            self.assertFalse(dialog.confirm_diff('fixture diff'))
            with patch.object(dialog,'confirm_diff',return_value=True):dialog.save()
            pump()
            self.assertIn('["general.border_size"] = 3',cfg.read_text())
            self.assertEqual(len(list(Path(td).glob('*.backup-*'))),1)
            self.assertIn('Nenhuma recarga',dialog.status.get())
            dialog.value.set('1');dialog.stage()
            self.assertEqual(dialog.staged,{'general:border_size':1})
            dialog.unstage()
            dialog.readback();pump()
            self.assertIn('divergente',dialog.details.get('1.0','end'))
            saved_code=dialog.code.get('1.0','end-1c')
            dialog.code.insert('end','\n'+m.BEGIN)
            with self.assertRaises(ValueError):dialog.proposed()
            dialog.code.delete('1.0','end');dialog.code.insert('1.0',saved_code)
            dialog.code.insert('end','\ninvalid Lua syntax!')
            with patch.object(dialog,'confirm_diff',return_value=True):dialog.save()
            pump();self.assertIn('Falha:',dialog.status.get())
            with patch.object(ui.messagebox,'askyesno',return_value=False):dialog.close()
            self.assertTrue(dialog.window.winfo_exists())
            dialog.window.destroy()
        root.destroy()

class EntrypointTests(unittest.TestCase):
    def test_app_entrypoint_uses_real_worker_queue_with_isolated_config(self):
        import app as application
        import hyprland_dialog as ui
        import hyprland_settings as m
        import tkinter as tk
        import time
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            cfg=Path(td)/'hyprland.lua';cfg.write_text('-- fixture\nhl.config({})\n')
            class Runtime:
                config=cfg;binary=Path('/fixture/Hyprland');instance={'instance':'fixture'}
                def options(self):return [m.Option({'name':'general:border_size','current':1})]
            original_dialog=ui.HyprlandDialog
            root=tk.Tk();root.withdraw()
            with patch.object(application.cm,'discover',return_value=[]),patch.object(application.palette,'current',return_value=None),patch.object(ui,'HyprlandDialog',side_effect=lambda app:original_dialog(app,runtime_factory=Runtime)):
                app=application.App(root,smoke=True)
                app.open_hyprland()
                end=time.monotonic()+3
                while time.monotonic()<end and (app.busy or app.hyprland_dialog.document is None):
                    root.update();time.sleep(.01)
                self.assertIsNotNone(app.hyprland_dialog.document)
                self.assertEqual(len(app.hyprland_dialog.tree.get_children()),1)
                first=app.hyprland_dialog;app.open_hyprland();self.assertIs(app.hyprland_dialog,first)
                first.code.insert('end','-- changed')
                first.save();first.reload()
                self.assertEqual(cfg.read_text(),'-- fixture\nhl.config({})\n')
                self.assertIn('smoke',first.status.get())
            for job in root.tk.call('after','info'):root.after_cancel(job)
            root.destroy()

if __name__=='__main__':unittest.main()
