#!/usr/bin/env python3
"""Default settings-center entrypoint; opening never changes settings."""
from __future__ import annotations
import argparse
import json
import tkinter as tk
from tkinter import ttk
from app import App

TITLE = 'hrprbar-config — Central de configurações'


class SettingsHome:
    def __init__(self, app: App):
        self.app = app
        self.root = app.root
        self.cursor_frames = [w for w in self.root.winfo_children() if w.winfo_manager() == 'pack']
        self.root.title(TITLE)
        self.navigation = ttk.Frame(self.root, padding=(14, 8))
        self.navigation.pack(side='top', fill='x', before=self.cursor_frames[0] if self.cursor_frames else None)
        self.home_button = ttk.Button(self.navigation, text='Início — Central de configurações', command=self.show_home)
        self.home_button.pack(side='left')
        ttk.Label(self.navigation, text='Alterações somente após confirmação.').pack(side='right')
        self.home = ttk.Frame(self.root, padding=24)
        ttk.Label(self.home, text='Configurações do seu desktop', font=('Liberation Sans', 22, 'bold')).pack(anchor='w', pady=(12, 16))
        ttk.Label(self.home, text='Hyprland, temas de ícones e cursores em um só aplicativo.', wraplength=780).pack(anchor='w', pady=(0, 24))
        self.hyprland_button = ttk.Button(self.home, text='Configurar Hyprland…', command=lambda: self.open_module('open_hyprland'))
        self.hyprland_button.pack(anchor='w', fill='x', pady=8)
        ttk.Label(self.home, text='Opções da versão em execução, busca por categoria e editor avançado da configuração Lua. Monitores, atalhos, regras e inicialização pelo editor avançado.', wraplength=800).pack(anchor='w', pady=(0, 16))
        self.icons_button = ttk.Button(self.home, text='Temas de ícones…', command=lambda: self.open_module('open_icons'))
        self.icons_button.pack(anchor='w', fill='x', pady=8)
        ttk.Label(self.home, text='Baixar, instalar e escolher temas de ícones. Instalar não aplica automaticamente.', wraplength=800).pack(anchor='w', pady=(0, 16))
        self.cursor_button = ttk.Button(self.home, text='Cursores — temas, tamanho e downloads', command=self.show_cursors)
        self.cursor_button.pack(anchor='w', fill='x', pady=8)
        ttk.Label(self.home, text='Prévias reais, nove fontes de temas e aplicação confirmada com backups.', wraplength=800).pack(anchor='w', pady=(0, 24))
        ttk.Label(self.home, text='Salvar não significa recarregar. Recarregar o Hyprland pode executar hooks da sua configuração. O editor Lua é avançado: alterações podem afetar toda a sessão.', wraplength=800).pack(anchor='w', pady=20)
        self.show_home()

    def open_module(self, name: str) -> None:
        if not self.app.busy:
            getattr(self.app, name)()

    def show_home(self) -> None:
        if self.app.busy and self.home.winfo_manager():
            return
        for frame in self.cursor_frames:
            frame.pack_forget()
        self.home.pack(fill='both', expand=True)

    def show_cursors(self) -> None:
        if self.app.busy:
            return
        self.home.pack_forget()
        for frame in self.cursor_frames:
            frame.pack(fill='both', expand=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=TITLE)
    parser.add_argument('--smoke-test', action='store_true', help='Construir a central sem aplicar alterações')
    args = parser.parse_args()
    root = tk.Tk(className='hrprbar-config')
    app = App(root, smoke=args.smoke_test)
    home = SettingsHome(app)
    if args.smoke_test:
        def finish() -> None:
            root.update_idletasks()
            assert home.home.winfo_manager() == 'pack'
            assert not any(w.winfo_manager() for w in home.cursor_frames)
            print(json.dumps({'title': root.title(), 'home': True, 'modules': ['Hyprland', 'Ícones', 'Cursores'], 'applied': app.applied}, ensure_ascii=False))
            root.destroy()
        root.after(700, finish)
    root.mainloop()


if __name__ == '__main__':
    main()
