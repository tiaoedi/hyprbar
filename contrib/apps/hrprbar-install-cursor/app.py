#!/usr/bin/env python3
"""Interface nativa Tk. Iniciar, listar e testar são operações somente de leitura."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tkinter.font as tkfont
from PIL import Image, ImageTk, ImageDraw
import cursor_manager as cm
import settings
import palette

TITLE = 'hrprbar-install cursor'
SHAPES = [('left_ptr','Ponteiro'),('hand2','Link'),('xterm','Texto'),('watch','Ocupado'),('crosshair','Precisão'),('fleur','Mover'),('sb_h_double_arrow','Horizontal'),('sb_v_double_arrow','Vertical')]


def tile(image: Image.Image, side: int = 92) -> Image.Image:
    canvas=Image.new('RGBA',(side,side),'#e5e7eb')
    draw=ImageDraw.Draw(canvas)
    for y in range(0,side,12):
        for x in range(0,side,12):
            if (x//12+y//12)%2: draw.rectangle((x,y,x+11,y+11),fill='#bbc1cb')
    img=image.copy()
    if max(img.size)>side-8: img.thumbnail((side-8,side-8),Image.Resampling.LANCZOS)
    canvas.alpha_composite(img,((side-img.width)//2,(side-img.height)//2))
    return canvas


class App:
    def __init__(self, root: tk.Tk, smoke: bool = False):
        self.root=root;self.smoke=smoke;self.themes=[];self.images={};self.detail_images=[];self.rendered=0;self.generation=0;self.load_generation=0;self.busy=False;self.applied=False;self.selected=None;self.queue=queue.Queue();self.last_applied=None
        root.title(TITLE);root.geometry('1120x820');root.minsize(900,700)
        families={f.casefold() for f in tkfont.families(root)}
        self.font_family='Hyprbar' if 'hyprbar' in families else ('Liberation Sans' if 'liberation sans' in families else 'Sans')
        for name in ('TkDefaultFont','TkTextFont','TkMenuFont','TkHeadingFont','TkCaptionFont','TkSmallCaptionFont','TkTooltipFont'):
            tkfont.nametofont(name).configure(family=self.font_family,size=11)
        style=ttk.Style(root);style.theme_use('clam');style.configure('Treeview',rowheight=64,font=(self.font_family,10));style.configure('TButton',padding=7)
        outer=ttk.Frame(root,padding=14);outer.pack(fill='both',expand=True)
        ttk.Label(outer,text=TITLE,font=(self.font_family,19,'bold')).pack(anchor='w')
        ttk.Label(outer,text='Veja os desenhos reais. Selecionar e ajustar tamanho não altera o cursor; somente “Aplicar tema”.').pack(anchor='w',pady=(2,12))
        toolbar=ttk.Frame(outer);toolbar.pack(fill='x')
        ttk.Label(toolbar,text='Buscar:').pack(side='left');self.search=tk.StringVar();ttk.Entry(toolbar,textvariable=self.search,width=28).pack(side='left',padx=7)
        self.search.trace_add('write',lambda *_:self.filter())
        self.refresh_button=ttk.Button(toolbar,text='Atualizar lista',command=self.load);self.refresh_button.pack(side='left',padx=4)
        self.online_dialog=None
        self.online_button=ttk.Button(toolbar,text='Baixar temas…',command=self.open_online);self.online_button.pack(side='right',padx=4)
        self.archive_button=ttk.Button(toolbar,text='Instalar novo: arquivo…',command=lambda:self.pick_install(False));self.archive_button.pack(side='right',padx=4)
        self.folder_button=ttk.Button(toolbar,text='Instalar novo: pasta…',command=lambda:self.pick_install(True));self.folder_button.pack(side='right',padx=4)
        body=ttk.Panedwindow(outer,orient='horizontal');body.pack(fill='both',expand=True,pady=12)
        left=ttk.Frame(body);right=ttk.Frame(body,padding=(14,0,0,0));body.add(left,weight=2);body.add(right,weight=3)
        self.tree=ttk.Treeview(left,show='tree',selectmode='browse');scroll=ttk.Scrollbar(left,orient='vertical',command=self.tree.yview);self.tree.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');self.tree.pack(fill='both',expand=True);self.tree.bind('<<TreeviewSelect>>',self.choose)
        self.heading=ttk.Label(right,text='Carregando temas…',font=(self.font_family,15,'bold'));self.heading.pack(anchor='w')
        self.path_label=ttk.Label(right,text='',wraplength=570);self.path_label.pack(anchor='w',pady=(3,9))
        line=ttk.Frame(right);line.pack(fill='x')
        ttk.Label(line,text='Tamanho nominal (px):').pack(side='left');self.size=tk.StringVar(value='32');self.size_box=ttk.Combobox(line,textvariable=self.size,values=['24','32','48','64','96'],state='readonly',width=7);self.size_box.pack(side='left',padx=8);self.size_box.bind('<<ComboboxSelected>>',lambda _:self.draw_details())
        self.apply_button=ttk.Button(line,text='Aplicar tema',command=self.do_apply,state='disabled');self.apply_button.pack(side='right')
        self.warning=ttk.Label(right,text='',wraplength=570,style='Warning.TLabel');self.warning.pack(anchor='w',pady=8)
        self.samples=ttk.Frame(right);self.samples.pack(fill='x',pady=5)
        ttk.Label(right,text='Estado / verificação (não equivale a atualização de todos os caches):',wraplength=550).pack(anchor='w',pady=(10,4))
        report_frame=ttk.Frame(right);report_frame.pack(fill='both',expand=True)
        self.report=tk.Text(report_frame,wrap='word',font=(self.font_family,10),height=10,state='disabled');report_scroll=ttk.Scrollbar(report_frame,command=self.report.yview);self.report.configure(yscrollcommand=report_scroll.set);report_scroll.pack(side='right',fill='y');self.report.pack(fill='both',expand=True)
        self.reopen_button=ttk.Button(right,text='Reabrir aplicativos…',command=self.reopen_info);self.reopen_button.pack(anchor='e',pady=5)
        self.status=tk.StringVar(value='Lendo temas instalados…');ttk.Label(outer,textvariable=self.status,wraplength=1050).pack(anchor='w')
        self.set_report('Nenhuma alteração realizada. Prévia usa a primeira imagem de animações. O tamanho nominal e as dimensões reais aparecem em cada desenho. Temas somente Hyprcursor são identificados, mas não aplicados por esta ferramenta.')
        self.theme_status=tk.StringVar(value='Tema do Hyprbar: lendo…');ttk.Label(outer,textvariable=self.theme_status,style='Muted.TLabel').pack(anchor='w')
        self.palette_spec=None;self.palette_pending=False
        self.root.after(50,self.poll);self.load();self.refresh_palette()
        self.root.bind('<FocusIn>',lambda e:self.refresh_palette() if e.widget is root else None,add='+')
        self.root.after(5000,self.poll_palette)

    def open_online(self) -> None:
        if self.busy:return
        if self.online_dialog is not None and self.online_dialog.window.winfo_exists():
            self.online_dialog.window.lift();return
        from online_dialog import OnlineDialog
        self.online_dialog=OnlineDialog(self)

    def poll_palette(self) -> None:
        self.refresh_palette();self.root.after(5000,self.poll_palette)

    def refresh_palette(self) -> None:
        if self.palette_pending:return
        self.palette_pending=True
        def ready(spec,error):
            self.palette_pending=False
            if error or spec==self.palette_spec:return
            self.palette_spec=spec;p=spec['colors'];style=ttk.Style(self.root)
            bg,fg,variant,outline=p['mSurface'],p['mOnSurface'],p['mSurfaceVariant'],p['mOutline']
            primary,onprimary,hover,onhover=p['mPrimary'],p['mOnPrimary'],p['mHover'],p['mOnHover']
            self.root.configure(background=bg)
            style.configure('.',background=bg,foreground=fg,bordercolor=outline,lightcolor=outline,darkcolor=outline,focuscolor=primary)
            for name in ('TFrame','TLabel','TPanedwindow'):style.configure(name,background=bg,foreground=fg)
            style.configure('Warning.TLabel',foreground=p['mSecondary']);style.configure('Muted.TLabel',foreground=p['mOnSurfaceVariant'])
            style.configure('TButton',background=variant,foreground=fg,bordercolor=outline,focuscolor=primary)
            style.map('TButton',background=[('disabled',bg),('pressed',primary),('active',hover)],foreground=[('disabled',p['mOnSurfaceVariant']),('pressed',onprimary),('active',onhover)],bordercolor=[('focus',primary)])
            style.configure('Treeview',background=bg,fieldbackground=bg,foreground=fg,bordercolor=outline)
            style.map('Treeview',background=[('selected',primary)],foreground=[('selected',onprimary)])
            for name in ('TEntry','TCombobox'):
                style.configure(name,background=variant,fieldbackground=variant,foreground=fg,arrowcolor=primary,insertcolor=fg,bordercolor=outline)
                style.map(name,fieldbackground=[('readonly',variant)],foreground=[('readonly',fg)],bordercolor=[('focus',primary)],selectbackground=[('focus',primary)],selectforeground=[('focus',onprimary)])
            for name in ('Vertical.TScrollbar','Horizontal.TScrollbar'):
                style.configure(name,background=outline,troughcolor=variant,bordercolor=bg,arrowcolor=fg,lightcolor=outline,darkcolor=outline)
                style.map(name,background=[('active',primary),('pressed',hover)])
            self.report.configure(background=variant,foreground=fg,insertbackground=fg,selectbackground=primary,selectforeground=onprimary,highlightbackground=outline,highlightcolor=primary)
            for key,value in {'*background':bg,'*foreground':fg,'*Listbox.background':variant,'*Listbox.foreground':fg,'*Listbox.selectBackground':primary,'*Listbox.selectForeground':onprimary,'*selectBackground':primary,'*selectForeground':onprimary,'*insertBackground':fg}.items():self.root.option_add(key,value)
            self.theme_status.set('Tema do Hyprbar: '+spec['name']+' • '+('claro' if spec['mode']=='light' else 'escuro')+(' (paleta de reserva; origem indisponível)' if spec['fallback'] else ''))
        self.worker(palette.current,ready)

    def worker(self,fn,done) -> None:
        def work():
            try: result=fn();self.queue.put((done,result,None))
            except Exception as exc: self.queue.put((done,None,exc))
        threading.Thread(target=work,daemon=True).start()

    def poll(self) -> None:
        try:
            for _ in range(100):
                done,result,error=self.queue.get_nowait()
                try: done(result,error)
                except Exception as exc:
                    self.status.set('Erro de interface: '+str(exc))
                    if self.smoke: raise
        except queue.Empty: pass
        self.root.after(50,self.poll)

    def set_report(self,text: str) -> None:
        self.report.configure(state='normal');self.report.delete('1.0','end');self.report.insert('1.0',text);self.report.configure(state='disabled')

    def load(self, installed_names: list[str] | None = None) -> None:
        if self.busy: return
        self.load_generation+=1;generation=self.load_generation
        self.status.set('Lendo temas instalados…')
        def ready(themes,error):
            if generation==self.load_generation:self.loaded(themes,error,installed_names)
        self.worker(cm.discover,ready)

    def loaded(self,themes,error,installed_names=None) -> None:
        if error: self.status.set('Falha na leitura: '+str(error));return
        self.themes=themes;self.images={};self.filter()
        self.status.set(f'{len(themes)} temas de cursor encontrados. Temas apenas de ícones são ignorados.')
        preferred=os.environ.get('XCURSOR_THEME','')
        chosen=next((t for t in themes if t.name==preferred),next((t for t in themes if t.xcursor),None))
        if installed_names:
            self.search.set('')
            chosen=next((t for t in themes if t.name==installed_names[0]),None) if len(installed_names)==1 else None
            self.tree.selection_remove(*self.tree.selection())
            self.clear_selection()
            self.status.set('Instalado(s): '+', '.join(installed_names)+'. Nada foi aplicado. Confira a prévia e use Aplicar tema.')
        if chosen and self.tree.exists(chosen.name): self.tree.selection_set(chosen.name);self.tree.see(chosen.name)
        def thumbs():
            for theme in themes:
                try:
                    image,_,_=cm.preview(theme.path/'cursors'/'left_ptr',32)
                    self.queue.put((lambda value,error:self.thumbnail(value), (theme.name,tile(image,56)),None))
                except (ValueError,OSError): continue
            return None
        self.worker(thumbs,lambda *_:None)

    def thumbnail(self,value) -> None:
        name,image=value
        if self.tree.exists(name):
            self.images[name]=ImageTk.PhotoImage(image);self.tree.item(name,image=self.images[name])

    def filter(self) -> None:
        old=self.tree.selection();self.tree.delete(*self.tree.get_children());term=self.search.get().casefold()
        for t in self.themes:
            if term not in t.name.casefold(): continue
            label=t.name+('  [somente Hyprcursor]' if not t.xcursor else '')
            self.tree.insert('','end',iid=t.name,text=label,image=self.images.get(t.name,''))
        if old and self.tree.exists(old[0]): self.tree.selection_set(old)

    def clear_selection(self) -> None:
        self.selected=None;self.generation+=1;self.rendered=0
        self.apply_button.configure(state='disabled')
        self.heading.configure(text='Escolha um tema na lista')
        self.path_label.configure(text='')
        self.warning.configure(text='Selecionar um tema não o aplica. Confira os tamanhos reais antes de aplicar.')
        for widget in self.samples.winfo_children():widget.destroy()
        self.detail_images=[]

    def choose(self,event=None) -> None:
        ids=self.tree.selection()
        if not ids:self.clear_selection();return
        self.selected=next(t for t in self.themes if t.name==ids[0]);self.heading.configure(text=self.selected.name);self.path_label.configure(text=str(self.selected.path))
        self.draw_details()

    def draw_details(self) -> None:
        t=self.selected
        if not t: return
        self.generation+=1;generation=self.generation
        self.apply_button.configure(state='disabled');self.warning.configure(text='Carregando imagens reais…')
        for w in self.samples.winfo_children(): w.destroy()
        self.detail_images=[]
        if not t.xcursor:
            self.warning.configure(text='Somente Hyprcursor: prévia e aplicação unificada indisponíveis. Instale também uma versão Xcursor para GTK/XWayland.');return
        requested=int(self.size.get())
        def render():
            result=[]
            for shape,label in SHAPES:
                try: image,nominal,sizes=cm.preview(t.path/'cursors'/shape,requested);result.append((label,image,nominal,sizes,None))
                except (OSError,ValueError) as exc: result.append((label,None,None,[],str(exc)))
            return result
        def ready(result,error):
            if generation!=self.generation:return
            if error: self.warning.configure(text=str(error));return
            pointer=result[0];sizes=pointer[3]
            if sizes:
                exact=settings.snap_size(requested,sizes);self.size_box.configure(values=[str(s) for s in sizes])
                if exact!=requested:
                    self.size.set(str(exact));self.draw_details();return
            warnings=[];self.rendered=0
            for i,(label,image,nominal,available,error) in enumerate(result):
                frame=ttk.Frame(self.samples,padding=3);frame.grid(row=i//4,column=i%4,sticky='nsew')
                ttk.Label(frame,text=label).pack()
                if image:
                    photo=ImageTk.PhotoImage(tile(image));self.detail_images.append(photo);ttk.Label(frame,image=photo).pack();self.rendered+=1
                    ttk.Label(frame,text=f'Nominal: {nominal}\nImagem: {image.width}×{image.height}',justify='center').pack()
                    ttk.Label(frame,text='Disponíveis:\n'+', '.join(map(str,available)),wraplength=125,justify='center').pack()
                    if nominal!=int(self.size.get()): warnings.append(label+': usa '+str(nominal))
                else: ttk.Label(frame,text='Sem imagem\ncompatível',justify='center').pack(pady=25)
            warning='Tamanho ajustado aos valores reais do ponteiro; sem interpolação na aplicação. Prévia reduzida somente se não couber.'
            if warnings: warning+=' Outros desenhos: '+', '.join(warnings)+'.'
            self.warning.configure(text=warning)
            self.apply_button.configure(state='normal' if sizes and not self.busy else 'disabled')
        self.worker(render,ready)

    def operation(self,fn,done) -> None:
        if self.busy:return
        self.busy=True
        for w in (self.apply_button,self.archive_button,self.folder_button,self.refresh_button,self.online_button):w.configure(state='disabled')
        def finished(result,error):
            self.busy=False
            for w in (self.archive_button,self.folder_button,self.refresh_button,self.online_button):w.configure(state='normal')
            self.draw_details();done(result,error)
        self.worker(fn,finished)

    def do_apply(self) -> None:
        if self.busy:return
        t=self.selected
        if not t or not t.xcursor:return
        size=int(self.size.get())
        if self.smoke: raise RuntimeError('Aplicação proibida em smoke-test')
        if not messagebox.askyesno('Aplicar tema?',f'Aplicar {t.name} com tamanho nominal {size}?\n\nSerão alinhados Hyprland, GTK3/4, GSettings, Xresources e ambiente de ativação. Backups serão criados. Nenhum aplicativo será fechado. Apps em execução podem precisar ser reabertos; monitores com escalas diferentes e sandboxes podem divergir.',parent=self.root):return
        self.status.set('Aplicando e verificando configurações…')
        def done(result,error):
            if error: messagebox.showerror('Falha na aplicação',str(error),parent=self.root);self.set_report('Falha: '+str(error));return
            self.applied=True;self.last_applied=(t,size);self.set_report(result);self.status.set('Configurações processadas; confira verificações e ressalvas. Nenhum aplicativo reiniciado.')
        self.operation(lambda:settings.apply(t,size),done)

    def pick_install(self,folder: bool) -> None:
        if self.smoke:return
        path=filedialog.askdirectory(title='Selecione a pasta do tema',parent=self.root) if folder else filedialog.askopenfilename(title='Selecione pacote de cursores',filetypes=[('Pacotes de tema','*.zip *.tar *.tar.gz *.tgz *.tar.xz *.tar.bz2 *.txz'),('Todos os arquivos','*')],parent=self.root)
        if not path:return
        dest=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))/'icons'
        if not messagebox.askyesno('Instalar novos cursores?',f'Validar e instalar todos os temas encontrados em:\n{path}\n\nDestino: {dest}\nTemas existentes nunca serão sobrescritos. O cursor ativo não será alterado.',parent=self.root):return
        self.status.set('Validando e instalando pacote local…')
        def done(result,error):
            if error: messagebox.showerror('Não foi possível instalar',str(error),parent=self.root);self.status.set('Instalação recusada: '+str(error));return
            names='\n'.join(str(p) for p in result);messagebox.showinfo('Temas instalados',names+'\n\nNada foi aplicado.',parent=self.root);self.load()
        self.operation(lambda:cm.install(Path(path),dest),done)

    def reopen_info(self) -> None:
        if not self.last_applied:
            messagebox.showinfo('Reabrir aplicativos','Aplique um tema primeiro. Nenhum aplicativo será encerrado sem confirmação explícita.',parent=self.root);return
        theme,size=self.last_applied
        self.worker(lambda:settings.stale_apps(theme.name,size),lambda apps,error:self.show_apps(apps or [],theme,size))

    def show_apps(self,apps,theme,size) -> None:
        dialog=tk.Toplevel(self.root);dialog.title('Reabrir aplicativos — confirmação necessária');dialog.geometry('760x420')
        ttk.Label(dialog,text='Ambiente antigo/ausente não prova cache incorreto. Feche trabalhos não salvos antes de reabrir.\nSomente navegadores Chromium nativos compatíveis têm reabertura assistida; demais apps: manual.',wraplength=730).pack(padx=12,pady=12)
        listing=tk.Listbox(dialog,height=10);listing.pack(fill='both',expand=True,padx=12)
        for p in apps:listing.insert('end',f"PID {p['pid']} {Path(p['exe']).name} — {p['theme']} / {p['size']}")
        if not apps:listing.insert('end','Nenhum ambiente divergente detectado nos clientes visíveis; caches ainda podem existir.')
        def reopen():
            selection=listing.curselection()
            if not selection or not apps:return
            p=apps[selection[0]]
            if Path(p['exe']).name not in ('chrome','chromium','chromium-browser','brave'):
                messagebox.showinfo('Reabertura manual','Este aplicativo não tem reabertura assistida segura. Salve o trabalho, feche-o e abra-o novamente pelo seu lançador.',parent=dialog);return
            if not messagebox.askyesno('Fechar navegador selecionado?',f"Reabrir {Path(p['exe']).name} (PID {p['pid']})?\n\nTODAS as janelas desse processo serão fechadas. Formulários, abas privadas e trabalho não salvo podem ser perdidos. A restauração de abas é solicitada, não garantida. Não prossiga sem salvar tudo.",parent=dialog):return
            def done(result,error):
                messagebox.showerror('Não reaberto',str(error),parent=dialog) if error else messagebox.showinfo('Reabertura solicitada',result,parent=dialog)
            self.operation(lambda:reopen_browser(p,theme.name,size),done)
        ttk.Button(dialog,text='Reabrir somente o selecionado…',command=reopen).pack(pady=10)


def reopen_browser(info: dict, theme: str,size: int) -> str:
    import subprocess,signal,time
    proc=Path('/proc')/str(info['pid'])
    exe=os.readlink(proc/'exe')
    if exe!=info['exe'] or Path(exe).name not in ('chrome','chromium','chromium-browser','brave'):raise ValueError('Processo não compatível ou mudou')
    argv=[os.fsdecode(x) for x in (proc/'cmdline').read_bytes().split(b'\0') if x]
    if any(a.startswith('--type=') for a in argv):raise ValueError('Selecione o processo principal, não um auxiliar')
    env=dict(os.fsdecode(x).split('=',1) for x in (proc/'environ').read_bytes().split(b'\0') if b'=' in x)
    if 'FLATPAK_ID' in env or 'SNAP' in env:raise ValueError('Navegador em sandbox: reabra manualmente')
    cwd=os.readlink(proc/'cwd');identity=(proc/'stat').read_text().split(') ',1)[1].split()[19]
    # Reconfere identidade imediatamente antes do sinal; nenhum kill forçado.
    if (proc/'stat').read_text().split(') ',1)[1].split()[19]!=identity:raise ValueError('Identidade mudou')
    os.kill(info['pid'],signal.SIGTERM)
    deadline=time.monotonic()+15
    while proc.exists() and time.monotonic()<deadline:time.sleep(.2)
    if proc.exists():raise RuntimeError('Navegador não encerrou; não será forçado nem duplicado. Reabra manualmente.')
    env.update(XCURSOR_THEME=theme,XCURSOR_SIZE=str(size),HYPRCURSOR_THEME=theme,HYPRCURSOR_SIZE=str(size))
    if '--restore-last-session' not in argv:argv.append('--restore-last-session')
    child=subprocess.Popen(argv,executable=exe,env=env,cwd=cwd,start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    time.sleep(1)
    if child.poll() not in (None,0):raise RuntimeError('O navegador encerrou com erro; reabra manualmente')
    return 'Lançamento solicitado com ambiente atualizado e restauração de sessão. Confira as abas e o desenho do cursor; restauração e cache visual não podem ser garantidos.'


def main() -> None:
    parser=argparse.ArgumentParser(description=TITLE)
    parser.add_argument('--list',action='store_true',help='Listar temas como JSON sem abrir interface')
    parser.add_argument('--smoke-test',action='store_true',help='Construir interface, renderizar amostra e fechar sem aplicar')
    args=parser.parse_args()
    if args.list:
        print(json.dumps([{'name':t.name,'path':str(t.path),'xcursor':t.xcursor,'hyprcursor':t.hyprcursor} for t in cm.discover()],ensure_ascii=False,indent=2));return
    root=tk.Tk(className='hrprbar-install-cursor');app=App(root,args.smoke_test)
    if args.smoke_test:
        import time
        deadline=time.monotonic()+20
        def check():
            if app.rendered and app.tree.get_children() and app.palette_spec:
                root.update_idletasks()
                def count_widgets(widget):
                    return 1+sum(count_widgets(child) for child in widget.winfo_children())
                heading_font=tkfont.Font(root=root,family=app.font_family,size=19,weight='bold')
                result={'title':root.title(),'themes':len(app.themes),'widgets':count_widgets(root),'heading_font_size':heading_font.actual('size'),'hyprbar_theme':app.theme_status.get(),'background':root.cget('background'),'rendered':app.rendered,'applied':app.applied,'width':root.winfo_width(),'height':root.winfo_height()}
                print(json.dumps(result,ensure_ascii=False));root.destroy()
            elif time.monotonic()>deadline:root.destroy();raise RuntimeError('Smoke-test: nenhuma amostra renderizada')
            else:root.after(100,check)
        root.after(200,check)
    root.mainloop()

if __name__=='__main__':main()
