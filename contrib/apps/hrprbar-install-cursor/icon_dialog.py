"""Portuguese icon theme manager; read-only until confirmed action buttons."""
from __future__ import annotations
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import ImageTk
import icons


class IconDialog:
    def __init__(self, app):
        self.app = app
        self.themes = []; self.selected = None; self.images = []
        self.generation = 0; self.discovery_generation = 0; self.online_dialog = None; self.catalog_dialog = None
        self.window = tk.Toplevel(app.root)
        self.window.title('Temas de ícones — instalar e trocar')
        self.window.geometry('1040x730'); self.window.minsize(880, 620)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        outer = ttk.Frame(self.window, padding=16); outer.pack(fill='both', expand=True)
        ttk.Label(outer,text='Temas de ícones',font=(app.font_family,18,'bold')).pack(anchor='w')
        ttk.Label(outer,text='Selecionar, visualizar ou instalar não aplica. Somente “Aplicar ícones…” altera GTK3/4 e GSettings icon-theme. Cursores não serão alterados.',wraplength=990).pack(anchor='w',pady=8)
        row = ttk.Frame(outer); row.pack(fill='x',pady=6)
        self.search = tk.StringVar()
        ttk.Label(row,text='Buscar instalados:').pack(side='left')
        ttk.Entry(row,textvariable=self.search,width=26).pack(side='left',padx=6)
        self.refresh_button = ttk.Button(row,text='Atualizar lista',command=self.refresh); self.refresh_button.pack(side='left',padx=4)
        self.online_button = ttk.Button(row,text='Baixar ícones — GitHub…',command=self.open_online); self.online_button.pack(side='right')
        row = ttk.Frame(outer); row.pack(fill='x',pady=6)
        self.archive_button = ttk.Button(row,text='Instalar arquivo…',command=lambda:self.pick_install(False)); self.archive_button.pack(side='left')
        self.folder_button = ttk.Button(row,text='Instalar pasta…',command=lambda:self.pick_install(True)); self.folder_button.pack(side='left',padx=6)
        self.catalog_button = ttk.Button(row,text='Temas GNOME-Look…',command=self.open_catalog); self.catalog_button.pack(side='left',padx=6)
        self.apply_button = ttk.Button(row,text='Aplicar ícones…',command=self.apply_selected,state='disabled'); self.apply_button.pack(side='right')
        ttk.Label(outer,text='Pacotes GitHub até 64 MiB; extração limitada a 20 mil entradas / 256 MiB. Sem scripts e sem substituir temas existentes.',wraplength=990).pack(anchor='w',pady=5)
        ttk.Style(app.root).configure('Icons.Treeview',rowheight=30)
        self.tree = ttk.Treeview(outer,style='Icons.Treeview',columns=('label','name'),show='headings',selectmode='browse',height=7)
        self.tree.heading('label',text='Tema instalado'); self.tree.heading('name',text='Identificador da pasta')
        self.tree.column('label',width=440); self.tree.column('name',width=330)
        scrollbar = ttk.Scrollbar(outer,command=self.tree.yview); self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right',fill='y'); self.tree.pack(fill='both',expand=True,pady=8)
        self.detail = tk.StringVar(value='Escolha um tema; nenhum será aplicado automaticamente.')
        ttk.Label(outer,textvariable=self.detail,wraplength=980).pack(anchor='w',pady=5)
        self.samples = ttk.Frame(outer); self.samples.pack(fill='x',pady=8)
        self.status = tk.StringVar(value='Lendo temas instalados…')
        ttk.Label(outer,textvariable=self.status,wraplength=980).pack(anchor='w',pady=8)
        self.search.trace_add('write',lambda *_:self.filter())
        self.tree.bind('<<TreeviewSelect>>',self.choose)
        self.refresh()
        self.controls(app.busy)

    def alive(self) -> bool:
        return bool(self.window.winfo_exists())

    def close(self) -> None:
        if self.app.busy:
            self.status.set('Operação em andamento; aguarde para fechar.'); return
        if self.online_dialog is not None and self.online_dialog.window.winfo_exists():
            self.online_dialog.close()
        if self.catalog_dialog is not None and self.catalog_dialog.window.winfo_exists():
            self.catalog_dialog.close()
        self.generation += 1; self.discovery_generation += 1
        self.window.destroy(); self.app.icon_dialog = None

    def controls(self, busy: bool) -> None:
        if not self.alive(): return
        for widget in (self.refresh_button,self.archive_button,self.folder_button,self.online_button,self.catalog_button):
            widget.configure(state='disabled' if busy else 'normal')
        self.apply_button.configure(state='normal' if self.selected and not busy and not self.app.smoke else 'disabled')
        if self.online_dialog is not None and self.online_dialog.window.winfo_exists(): self.online_dialog.controls(busy)
        if self.catalog_dialog is not None and self.catalog_dialog.window.winfo_exists(): self.catalog_dialog.controls(busy)

    def refresh(self, names: list[str] | None = None) -> None:
        if self.app.busy: return
        self.discovery_generation += 1; generation = self.discovery_generation
        self.status.set('Lendo temas de ícones instalados…')
        def ready(themes,error):
            if not self.alive() or generation != self.discovery_generation: return
            if error: self.status.set('Falha: '+str(error)); return
            self.themes = themes
            self.filter()
            if names:
                self.search.set(''); self.tree.selection_remove(*self.tree.selection()); self.choose()
                if len(names) == 1 and self.tree.exists(names[0]): self.tree.selection_set(names[0]); self.choose()
                self.status.set('Instalado(s): '+', '.join(names)+'. Nada foi aplicado; escolha e confirme Aplicar ícones…')
            else: self.status.set(f'{len(themes)} temas de ícones válidos. Selecionar não aplica.')
        self.app.worker(icons.discover,ready)

    def filter(self) -> None:
        old = self.tree.selection(); self.tree.delete(*self.tree.get_children())
        term = self.search.get().casefold()
        for theme in self.themes:
            if term in (theme.name+' '+theme.label).casefold():
                self.tree.insert('','end',iid=theme.name,values=(theme.label,theme.name))
        if old and self.tree.exists(old[0]): self.tree.selection_set(old)
        self.choose()

    def choose(self, _=None) -> None:
        self.generation += 1; generation = self.generation
        ids = self.tree.selection()
        self.selected = next((t for t in self.themes if ids and t.name == ids[0]),None)
        self.images = []
        for widget in self.samples.winfo_children(): widget.destroy()
        self.controls(self.app.busy)
        theme = self.selected
        if theme is None:
            self.detail.set('Escolha um tema; nenhum será aplicado automaticamente.'); return
        self.detail.set(theme.label+'\n'+str(theme.path)+'\nCarregando imagens reais PNG/SVG/XPM…')
        def render():
            found = []; failures = []
            for sample in theme.samples[:6]:
                try: found.append((sample.name,icons.preview(sample)))
                except (ValueError,OSError) as exc: failures.append(str(exc))
            return found, failures
        def ready(result,error):
            if not self.alive() or generation != self.generation: return
            if error: self.detail.set(theme.label+'\n'+str(theme.path)+'\nPrévia indisponível: '+str(error)); return
            found, failures = result
            for i,(name,image) in enumerate(found):
                frame = ttk.Frame(self.samples,padding=3); frame.grid(row=0,column=i,sticky='n')
                photo = ImageTk.PhotoImage(image); self.images.append(photo)
                ttk.Label(frame,image=photo).pack()
                ttk.Label(frame,text=name,wraplength=140).pack()
            self.detail.set(theme.label+'\n'+str(theme.path)+'\n'+(f'{len(found)} prévia(s) reais; redução apenas para exibição.' if found else 'Prévia indisponível: '+'; '.join(failures[:1])))
        self.app.worker(render,ready)

    def destination(self) -> Path:
        return Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))/'icons'

    def pick_install(self, folder: bool) -> None:
        if self.app.busy or self.app.smoke: return
        path = filedialog.askdirectory(title='Pasta do tema de ícones',parent=self.window) if folder else filedialog.askopenfilename(title='Pacote de ícones',parent=self.window,filetypes=[('Temas de ícones','*.zip *.tar *.tar.gz *.tgz *.tar.xz *.tar.bz2 *.txz'),('Todos','*')])
        if not path: return
        destination = self.destination()
        if not messagebox.askyesno('Instalar temas de ícones?',f'Origem: {path}\nDestino: {destination}\n\nValidar e instalar sem substituir temas? Nada será aplicado; nenhum script será executado.',parent=self.window): return
        self.status.set('Validando e instalando ícones…')
        def done(paths,error):
            if error: self.status.set('Instalação recusada: '+str(error)); return
            self.refresh([p.name for p in paths])
        self.app.operation(lambda:icons.install(Path(path),destination),done)

    def open_catalog(self) -> None:
        if self.app.busy or self.app.smoke: return
        if self.catalog_dialog is not None and self.catalog_dialog.window.winfo_exists():
            self.catalog_dialog.window.lift(); return
        from icon_catalog_dialog import IconCatalogDialog
        self.catalog_dialog = IconCatalogDialog(self)

    def open_online(self) -> None:
        if self.app.busy or self.app.smoke: return
        if self.online_dialog is not None and self.online_dialog.window.winfo_exists(): self.online_dialog.window.lift(); return
        from online_dialog import OnlineDialog
        self.online_dialog = OnlineDialog(self.app,icon_owner=self)

    def apply_selected(self) -> None:
        if self.app.busy or self.app.smoke or self.selected is None: return
        theme = self.selected
        if not messagebox.askyesno('Aplicar tema de ícones?',f'Aplicar {theme.name}?\n\nSerão alterados somente gtk-icon-theme-name em GTK3/4 e icon-theme em GSettings, com backups e verificação. Cursores, compositor e barra não serão alterados. Nenhum aplicativo será reiniciado. Qt, sandboxes e apps abertos podem manter configurações próprias.',parent=self.window): return
        self.status.set('Aplicando e verificando somente ícones…')
        def done(report,error): self.status.set('Falha: '+str(error) if error else report)
        self.app.operation(lambda:icons.apply(theme),done)
