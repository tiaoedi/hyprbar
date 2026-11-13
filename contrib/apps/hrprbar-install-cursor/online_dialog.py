"""Portuguese, explicitly loaded catalog on the existing Tk worker queue."""
from __future__ import annotations
import tkinter as tk
import os
from pathlib import Path
from tkinter import ttk, messagebox
import online
import webbrowser
from navigation import add_home_button


class OnlineDialog:
    def __init__(self, app, *, icon_owner=None):
        self.app = app
        self.icon_owner = icon_owner
        if icon_owner is not None:
            import icons
            self.families = icons.FAMILIES
        else:
            self.families = online.FAMILIES
        self.assets: list[online.Asset] = []
        self.generation = 0
        self.window = tk.Toplevel(app.root)
        self.window.title('Baixar temas — GitHub Releases')
        self.window.geometry('1040x800'); self.window.minsize(900, 680)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.home_button = add_home_button(app, self.window, self.close)
        outer = ttk.Frame(self.window, padding=16); outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='Baixar temas de ícones' if icon_owner is not None else 'Baixar temas de cursor', font=(app.font_family, 18, 'bold')).pack(anchor='w')
        ttk.Label(outer, text='Pacotes Linux publicados em GitHub Releases (até 64 MiB). Nada é baixado ao abrir; instalar nunca aplica o tema.', wraplength=990).pack(anchor='w', pady=(5, 12))
        line = ttk.Frame(outer); line.pack(fill='x')
        ttk.Label(line, text='Família:').pack(side='left')
        self.family = tk.StringVar(value='Todos os repositórios')
        self.family_box = ttk.Combobox(line, textvariable=self.family, values=['Todos os repositórios']+list(self.families)+['Personalizado'], state='readonly', width=24)
        self.family_box.pack(side='left', padx=8); self.family_box.bind('<<ComboboxSelected>>', self.select_family)
        self.fetch_button = ttk.Button(line, text='Buscar versões/temas', command=self.fetch); self.fetch_button.pack(side='right')
        row = ttk.Frame(outer); row.pack(fill='x', pady=10)
        ttk.Label(row, text='Repositório GitHub:').pack(side='left')
        self.repo = tk.StringVar(value='')
        self.repo_entry = ttk.Entry(row, textvariable=self.repo); self.repo_entry.pack(side='left', fill='x', expand=True, padx=8)
        ttk.Label(outer, text='Aceita owner/repo ou https://github.com/owner/repo; não instala código-fonte nem executa scripts.', wraplength=990).pack(anchor='w')
        external = ttk.Frame(outer); external.pack(fill='x',pady=(8,2))
        self.flaticon_button = ttk.Button(external,text='Flaticon — imagens de cursor ↗',command=lambda:self.open_external('https://www.flaticon.com/br/icones-gratis/cursor')); self.flaticon_button.pack(side='left',padx=(0,8))
        self.custom_cursor_button = ttk.Button(external,text='Custom Cursor — catálogo externo ↗',command=lambda:self.open_external('https://custom-cursor.com/es/top-downloaded-cursors')); self.custom_cursor_button.pack(side='left')
        external_more = ttk.Frame(outer); external_more.pack(fill='x', pady=(2, 4))
        self.gnome_look_button = ttk.Button(external_more, text='GNOME-Look — catálogo externo ↗', command=lambda: self.open_external('https://www.gnome-look.org/browse?cat=132&ord=latest')); self.gnome_look_button.pack(side='left')
        ttk.Label(outer,text='Sites externos abrem no navegador somente ao clicar. Flaticon: imagens PNG/SVG; não são temas Linux instaláveis. Custom Cursor pode oferecer conteúdo para navegador/Windows. GNOME-Look: catálogo externo; conteúdo gráfico e pacotes não garantem compatibilidade. Para instalar localmente, obtenha um arquivo de tema compatível com Linux e com o tipo escolhido (ícones ou cursores). Respeite licença/atribuição; login no site, sem download ou instalação automática por este link.',wraplength=860).pack(anchor='w')
        row = ttk.Frame(outer); row.pack(fill='x', pady=10)
        ttk.Label(row, text='Filtrar variantes:').pack(side='left')
        self.search = tk.StringVar(); ttk.Entry(row, textvariable=self.search).pack(side='left', fill='x', expand=True, padx=8)
        listing = ttk.Frame(outer); listing.pack(fill='both', expand=True)
        ttk.Style(app.root).configure('Catalog.Treeview', rowheight=30)
        self.tree = ttk.Treeview(listing, style='Catalog.Treeview', columns=('name','size','version','repo'), show='headings', selectmode='browse', height=8)
        for key, title, width in [('name','Pacote / variante',350), ('size','Tamanho',100), ('version','Versão',100), ('repo','Origem GitHub',280)]:
            self.tree.heading(key, text=title); self.tree.column(key, width=width, minwidth=75)
        scrollbar = ttk.Scrollbar(listing, command=self.tree.yview); self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y'); self.tree.pack(fill='both', expand=True)
        self.detail = tk.StringVar(value='Selecione um pacote para conferir a origem e a integridade.')
        ttk.Label(outer, textvariable=self.detail, wraplength=990).pack(anchor='w', pady=10)
        self.status = tk.StringVar(value=f'{len(self.families)} repositórios configurados: '+', '.join(self.families)+'. Clique em Buscar versões/temas.')
        ttk.Label(outer, textvariable=self.status, wraplength=990).pack(anchor='w', pady=5)
        row = ttk.Frame(outer); row.pack(fill='x', pady=8)
        ttk.Label(row, text='Após instalar: escolha o tema, confira a prévia e use “Aplicar ícones…” com confirmação.' if icon_owner is not None else 'Após instalar: selecione o tema na janela principal, confira a prévia e clique em Aplicar tema.', wraplength=700).pack(side='left')
        self.install_button = ttk.Button(row, text='Baixar e instalar', command=lambda: self.install_selected(), state='disabled'); self.install_button.pack(side='right')
        self.search.trace_add('write', lambda *_: self.filter())
        self.repo.trace_add('write', self.repo_changed)
        self.tree.bind('<<TreeviewSelect>>', self.select_asset)
        self.window.update_idletasks()

    def open_external(self, url: str) -> None:
        if self.app.busy or self.app.smoke:return
        if not webbrowser.open(url):
            self.status.set('Não foi possível abrir o navegador; site externo: '+url)

    def close(self) -> None:
        if self.app.busy:
            self.status.set('Operação em andamento; aguarde a conclusão antes de fechar.'); return
        self.window.destroy()
        if self.icon_owner is not None:self.icon_owner.online_dialog = None
        else:self.app.online_dialog = None

    def repo_changed(self, *_) -> None:
        self.family.set('Personalizado')
        self.invalidate()

    def select_family(self, _=None) -> None:
        name = self.family.get()
        if name in self.families:
            self.repo.set(self.families[name]); self.family.set(name)
        elif name == 'Todos os repositórios':
            self.repo.set(''); self.family.set(name)
        self.invalidate()

    def invalidate(self) -> None:
        self.generation += 1
        self.assets = []
        self.filter()
        self.status.set('Origem alterada; clique em Buscar versões/temas.')

    def filter(self) -> None:
        self.tree.delete(*self.tree.get_children())
        term = self.search.get().casefold()
        for index, asset in enumerate(self.assets):
            if term in (asset.name+' '+asset.repo+' '+asset.version).casefold():
                self.tree.insert('', 'end', iid=str(index), values=(asset.name, f'{asset.size/1048576:.2f} MiB', asset.version, asset.repo))
        self.select_asset()

    def selected_asset(self) -> online.Asset | None:
        selection = self.tree.selection()
        return self.assets[int(selection[0])] if selection else None

    def select_asset(self, _=None) -> None:
        asset = self.selected_asset()
        self.install_button.configure(state='normal' if asset and not self.app.busy else 'disabled')
        self.detail.set((asset.url+'\n'+('SHA256 publicado: '+asset.digest if asset.digest else 'Sem SHA256 publicado; transporte HTTPS não é assinatura do autor.')) if asset else 'Selecione um pacote para conferir a origem e a integridade.')

    def controls(self, busy: bool) -> None:
        self.fetch_button.configure(state='disabled' if busy else 'normal')
        self.repo_entry.configure(state='disabled' if busy else 'normal')
        self.family_box.configure(state='disabled' if busy else 'readonly')
        for button in (self.flaticon_button,self.custom_cursor_button,self.gnome_look_button):button.configure(state='disabled' if busy or self.app.smoke else 'normal')
        self.select_asset()

    def fetch(self) -> None:
        if self.app.busy or self.app.smoke: return
        self.invalidate()
        generation = self.generation
        sources = list(self.families.values()) if self.family.get() == 'Todos os repositórios' else [self.repo.get()]
        self.status.set('Buscando últimas versões publicadas nos repositórios ativos…')
        def done(result, error):
            self.controls(False)
            if generation != self.generation: return
            if error:
                self.status.set('Falha: '+str(error)); return
            self.assets = list(result.assets)
            self.filter()
            self.status.set('\n'.join(f'{repo}: {status}' for repo, status in result.statuses.items()))
        self.app.operation(lambda: online.catalog(sources), done)
        self.controls(True)

    def install_selected(self) -> None:
        if self.app.busy or self.app.smoke: return
        asset = self.selected_asset()
        if asset is None: return
        destination = Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))/'icons'
        if not messagebox.askyesno('Baixar e instalar?', f'Origem: {asset.repo}\nVersão: {asset.version}\nPacote: {asset.name}\nDestino: {destination}\n\nValidar e instalar sem sobrescrever temas? Nada será aplicado; nenhum script será executado.', parent=self.window):
            return
        self.status.set('Baixando, validando e instalando… aguarde.')
        def done(paths, error):
            self.controls(False)
            if error:
                self.status.set('Instalação recusada: '+str(error)); return
            self.close()
            if self.icon_owner is not None:self.icon_owner.refresh([path.name for path in paths])
            else:self.app.load([path.name for path in paths])
        if self.icon_owner is not None:
            import icons
            install = icons.install_asset
        else:install = online.install_asset
        self.app.operation(lambda: install(asset, destination), done)
        self.controls(True)
