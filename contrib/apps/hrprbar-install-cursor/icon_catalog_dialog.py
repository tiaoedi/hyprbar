"""Local, curated icon catalog; no network or desktop changes on opening."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

import icon_catalog
from navigation import add_home_button


class IconCatalogDialog:
    def __init__(self, owner):
        self.owner = owner
        self.app = owner.app
        self._busy = self.app.busy
        self.window = tk.Toplevel(owner.window)
        self.window.title('Catálogo curado — temas de ícones')
        self.window.geometry('1040x760')
        self.window.minsize(900, 680)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.home_button = add_home_button(self.app, self.window, self.close)
        outer = ttk.Frame(self.window, padding=16)
        outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='Catálogo curado de ícones',
                  font=(self.app.font_family, 18, 'bold')).pack(anchor='w')
        ttk.Label(outer, text='6 temas com origem e limitações verificadas. Abrir não baixa nem aplica; '
                  'cinco pacotes permanecem bloqueados, sem reduzir as regras de segurança.',
                  wraplength=850).pack(anchor='w', pady=(5, 10))
        row = ttk.Frame(outer)
        row.pack(fill='x', pady=(0, 8))
        ttk.Label(row, text='Buscar tema ou autor:').pack(side='left')
        self.search = tk.StringVar()
        self.search_entry = ttk.Entry(row, textvariable=self.search)
        self.search_entry.pack(side='left', fill='x', expand=True, padx=(8, 0))
        listing = ttk.Frame(outer)
        listing.pack(fill='both', expand=True)
        ttk.Style(self.app.root).configure('IconCatalog.Treeview', rowheight=30)
        self.tree = ttk.Treeview(listing, style='IconCatalog.Treeview',
                                columns=('name', 'author', 'status'), show='headings',
                                selectmode='browse', height=6)
        for key, title, width in (('name', 'Tema', 380), ('author', 'Autor', 150),
                                  ('status', 'Instalação automática', 280)):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, minwidth=100)
        scrollbar = ttk.Scrollbar(listing, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self.tree.pack(fill='both', expand=True)
        self.detail = tk.StringVar()
        self.detail_label = ttk.Label(outer, textvariable=self.detail, wraplength=850,
                                      justify='left')
        self.detail_label.pack(fill='x', pady=(10, 6))
        self.status = tk.StringVar(value='6 temas curados. Selecione para conferir origem, licença e limitações.')
        self.status_label = ttk.Label(outer, textvariable=self.status, wraplength=850)
        self.status_label.pack(fill='x', pady=5)
        row = ttk.Frame(outer)
        row.pack(fill='x', pady=(6, 0))
        self.page_button = ttk.Button(row, text='Abrir página do tema ↗', command=self.open_page, state='disabled')
        self.page_button.pack(side='left')
        self.archive_button = ttk.Button(row, text='Instalar arquivo…', command=self.install_archive)
        self.archive_button.pack(side='left', padx=8)
        self.install_button = ttk.Button(row, text='Baixar e instalar', command=self.install_selected, state='disabled')
        self.install_button.pack(side='right')
        ttk.Label(outer, text='Instalar nunca aplica. Páginas externas abrem somente ao clicar; '
                  'arquivos manuais continuam sujeitos à validação, sem scripts ou sobrescrita.',
                  wraplength=850).pack(fill='x', pady=(10, 0))
        self.search.trace_add('write', lambda *_: self.filter())
        self.tree.bind('<<TreeviewSelect>>', self.select_source)
        self.filter()

    def selected_source(self):
        selection = self.tree.selection()
        return next((source for source in icon_catalog.SOURCES
                     if selection and source.key == selection[0]), None)

    def filter(self):
        previous = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        term = self.search.get().casefold()
        for source in icon_catalog.SOURCES:
            if term in (source.name+' '+source.author+' '+source.reason).casefold():
                self.tree.insert('', 'end', iid=source.key,
                                 values=(source.name, source.author,
                                         'Pacote verificado' if source.package else 'Bloqueado — consulte detalhes'))
        if previous and self.tree.exists(previous[0]):
            self.tree.selection_set(previous[0])
        self.select_source()

    def select_source(self, _=None):
        source = self.selected_source()
        if source is None:
            self.detail.set('Selecione um tema para conferir a página original, licença e motivo da disponibilidade.')
        else:
            self.detail.set(f'{source.name}\nAutor: {source.author}\nPágina: {source.page}\n'
                            f'Licença: {source.license}\n{source.reason}')
            if source.package:
                package = source.package
                self.detail.set(self.detail.get()+f'\nPacote: {package.name} — {package.repo}'
                                f'\nCommit: {package.commit}\nTamanho: {package.size} bytes'
                                f'\nSHA256: {package.sha256}')
        blocked = self._busy or self.app.busy or self.app.smoke
        self.install_button.configure(state='normal' if source and source.package and not blocked else 'disabled')
        self.page_button.configure(state='normal' if source and not blocked else 'disabled')
        self.archive_button.configure(state='disabled' if blocked else 'normal')

    def controls(self, busy):
        if not self.window.winfo_exists():
            return
        self._busy = busy
        self.search_entry.configure(state='disabled' if busy else 'normal')
        self.select_source()

    def open_page(self):
        if self._busy or self.app.busy or self.app.smoke:
            return
        source = self.selected_source()
        if source is None:
            return
        try:
            if not webbrowser.open(source.page):
                self.status.set('Não foi possível abrir o navegador; página: '+source.page)
        except Exception as exc:
            self.status.set('Falha ao abrir '+source.page+': '+str(exc))

    def install_archive(self):
        if self._busy or self.app.busy or self.app.smoke:
            return
        self.owner.pick_install(False)

    def install_selected(self):
        if self._busy or self.app.busy or self.app.smoke:
            return
        source = self.selected_source()
        if source is None or source.package is None:
            return
        destination = self.owner.destination()
        package = source.package
        if not messagebox.askyesno(
                'Baixar e instalar ícones?',
                f'Tema: {source.name}\nURL: {package.url}\nSHA256: {package.sha256}'
                f'\nDestino: {destination}\n\nValidar e instalar sem substituir temas? '
                'Nada será aplicado; nenhum script será executado.', parent=self.window):
            return
        self.status.set('Baixando, validando SHA256 e instalando… aguarde.')

        def done(paths, error):
            self.controls(False)
            if error:
                self.status.set('Instalação recusada: '+str(error))
                return
            self.close()
            self.owner.refresh([path.name for path in paths])

        self.app.operation(lambda: icon_catalog.install_source(source, destination), done)
        self.controls(True)

    def close(self):
        if self._busy or self.app.busy:
            self.status.set('Operação em andamento; aguarde a conclusão antes de fechar.')
            return
        self.window.destroy()
        self.owner.catalog_dialog = None
