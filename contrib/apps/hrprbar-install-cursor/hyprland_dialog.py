"""Explicit, staged Hyprland configuration dialog; opening is read-only."""
from __future__ import annotations
import json
import tkinter as tk
from tkinter import ttk, messagebox
import hyprland_settings as hs
from navigation import add_home_button


class HyprlandDialog:
    def __init__(self,app,runtime_factory=hs.Runtime):
        self.app=app
        self.runtime_factory=runtime_factory
        self.runtime=None
        self.document=None
        self.options={}
        self.staged={}
        self.saved_values={}
        self.selected=None
        self.drafts={}
        self._editor_name=None
        self._loading_editor=False
        self.busy=False
        self.window=tk.Toplevel(app.root)
        self.window.title('Configurar Hyprland — hrprbar-install cursor')
        self.window.geometry('1180x850')
        self.window.minsize(900,650)
        self.window.protocol('WM_DELETE_WINDOW',self.close)

        self.style=ttk.Style(self.window)
        self.style.configure('Hyprland.Treeview',rowheight=29)
        self.style.configure('Hyprland.Apply.TButton',font=(app.font_family,11,'bold'),padding=(12,8))
        self._palette_colors=None
        self._palette_job=None
        self.window.bind('<Destroy>',self._cancel_palette_poll,add='+')
        outer=ttk.Frame(self.window,padding=(12,6));outer.pack(fill='both',expand=True)
        titlebar=ttk.Frame(outer);titlebar.pack(fill='x')
        ttk.Label(titlebar,text='Central de configurações do Hyprland',font=(app.font_family,17,'bold')).pack(side='left')
        self.home_button=add_home_button(app,self.window,self.close,parent=titlebar)
        ttk.Label(outer,text='Editar prepara alterações apenas na memória. Aplicar e recarregar salva e executa o Lua completo e hooks somente após sua confirmação.',wraplength=850).pack(anchor='w',pady=5)
        self.location=tk.StringVar(value='Localizando sessão e configuração ativa…')
        ttk.Label(outer,textvariable=self.location,wraplength=1100).pack(anchor='w')
        self.tabs=ttk.Notebook(outer,style='Hyprland.TNotebook');self.tabs.pack(fill='both',expand=True,pady=8)
        explorer=ttk.Frame(self.tabs,padding=8);advanced=ttk.Frame(self.tabs,padding=8)
        self.tabs.add(explorer,text='Todas as opções');self.tabs.add(advanced,text='Avançado: configuração Lua completa')
        quick=ttk.Frame(explorer);quick.pack(fill='x',pady=(0,8))
        ttk.Label(quick,text='Efeito de vidro (blur):',font=(app.font_family,11,'bold')).pack(side='left')
        self.blur_value=tk.StringVar()
        self.blur_box=ttk.Combobox(quick,textvariable=self.blur_value,values=('Ativado','Desativado'),state='disabled',width=14)
        self.blur_box.pack(side='left',padx=8)
        self.blur_box.bind('<<ComboboxSelected>>',self.blur_selected)
        self.blur_status=tk.StringVar(value='Indisponível: carregando opções.')
        self.blur_status_label=ttk.Label(explorer,textvariable=self.blur_status,wraplength=800)
        self.blur_status_label.pack(anchor='w')
        self.blur_status_label.bind('<Configure>',lambda event:self.blur_status_label.configure(wraplength=max(240,explorer.winfo_width()-16)))
        self.blur_note=ttk.Label(explorer,text='Ativado: blur e 90% de opacidade nas janelas normais inteiras (texto também). Desativado: sem blur e 100%. Tela cheia e regras não mudam. Pendente até Aplicar e recarregar.',wraplength=800)
        self.blur_note.pack(anchor='w',pady=(0,8))
        bar=ttk.Frame(explorer);bar.pack(fill='x')
        ttk.Label(bar,text='Buscar nome / descrição:').pack(side='left')
        self.search=tk.StringVar();ttk.Entry(bar,textvariable=self.search,width=28).pack(side='left',padx=6)
        ttk.Label(bar,text='Categoria:').pack(side='left')
        self.category=tk.StringVar(value='Todas')
        self.category_box=ttk.Combobox(bar,textvariable=self.category,state='readonly',width=28,values=['Todas']);self.category_box.pack(side='left',padx=6)
        self.refresh_button=ttk.Button(bar,text='Reler do compositor / arquivo',command=self.load);self.refresh_button.pack(side='right')
        body=ttk.Panedwindow(explorer,orient='horizontal');body.pack(fill='both',expand=True,pady=8)
        left=ttk.Frame(body);right=ttk.Frame(body,padding=(12,0,0,0));body.add(left,weight=3);body.add(right,weight=2)
        self.tree=ttk.Treeview(left,columns=('current','staged'),show='tree headings',selectmode='browse',height=10,style='Hyprland.Treeview')
        self.tree.heading('#0',text='Opção');self.tree.heading('current',text='Em execução');self.tree.heading('staged',text='Pendente')
        self.tree.column('#0',width=280);self.tree.column('current',width=110);self.tree.column('staged',width=110)
        horizontal=ttk.Scrollbar(left,orient='horizontal',command=self.tree.xview)
        horizontal.pack(side='bottom',fill='x')
        scroll=ttk.Scrollbar(left,command=self.tree.yview);self.tree.configure(yscrollcommand=scroll.set,xscrollcommand=horizontal.set);scroll.pack(side='right',fill='y');self.tree.pack(fill='both',expand=True)
        self.tree.bind('<<TreeviewSelect>>',self.choose)
        self.details=tk.Text(right,height=12,wrap='word',state='disabled',font=(app.font_family,10))
        self.details.pack(fill='both',expand=True)
        edit=ttk.Frame(right);edit.pack(fill='x',pady=6)
        ttk.Label(edit,text='Novo valor:').pack(side='left');self.value=tk.StringVar()
        self.value_entry=ttk.Entry(edit,textvariable=self.value);self.value_entry.pack(side='left',fill='x',expand=True,padx=5)
        self.bool_value=tk.StringVar()
        self.bool_box=ttk.Combobox(edit,textvariable=self.bool_value,values=('Ativado','Desativado'),state='readonly',width=16)
        self.bool_box.bind('<<ComboboxSelected>>',self.boolean_selected)
        self.count=tk.StringVar(value='0 alterações pendentes')
        ttk.Label(explorer,textvariable=self.count).pack(anchor='w')
        warning=ttk.Label(advanced,text='ATENÇÃO: poder completo. Este arquivo Lua pode executar qualquer comando com suas permissões ao recarregar. Monitores, atalhos, regras, animações e inicialização ficam no código real abaixo; módulos require/dofile externos não são expandidos. luac -p verifica apenas sintaxe, não a API nem efeitos do Lua.',wraplength=820,style='Warning.TLabel')
        warning.pack(fill='x',anchor='w',pady=(0,8))
        warning.bind('<Configure>',lambda event: warning.configure(wraplength=max(240,event.width)))
        codeframe=ttk.Frame(advanced);codeframe.pack(fill='both',expand=True)
        self.code=tk.Text(codeframe,wrap='none',undo=True,font=('monospace',11));ys=ttk.Scrollbar(codeframe,command=self.code.yview);xs=ttk.Scrollbar(advanced,orient='horizontal',command=self.code.xview);self.code.configure(yscrollcommand=ys.set,xscrollcommand=xs.set);ys.pack(side='right',fill='y');self.code.pack(fill='both',expand=True);xs.pack(fill='x')
        ttk.Label(advanced,text='Aplicar e recarregar combina este texto completo com os valores pendentes no bloco gerenciado final. Não remova seus marcadores parcialmente.',wraplength=850).pack(anchor='w',pady=4)
        actions=ttk.Frame(outer);actions.pack(fill='x')
        self.apply_button=ttk.Button(actions,text='Aplicar e recarregar',command=self.apply,style='Hyprland.Apply.TButton');self.apply_button.grid(row=0,column=0,sticky='w')
        actions.columnconfigure(1,weight=1)
        ttk.Button(actions,text='Fechar',command=self.close).grid(row=0,column=1,sticky='nse')
        self.status=tk.StringVar(value='Somente leitura: carregando…');ttk.Label(outer,textvariable=self.status,wraplength=1100).pack(anchor='w',pady=8)
        self.search.trace_add('write',lambda *_:self.filter())
        self.category.trace_add('write',lambda *_:self.filter())
        self.value.trace_add('write',self.value_changed)
        self._poll_palette()
        self.load()

    BLUR = 'decoration:blur:enabled'
    GLASS_ON = {BLUR:True, 'decoration:active_opacity':0.9,
                'decoration:inactive_opacity':0.9}
    GLASS_OFF = {BLUR:False, 'decoration:active_opacity':1.0,
                 'decoration:inactive_opacity':1.0}

    def glass_schema_issue(self):
        """The preset is atomic: both directions must validate for every key."""
        for name,on in self.GLASS_ON.items():
            option=self.options.get(name)
            if option is None or not option.editable or type(option.current) is not type(on):
                return name+' ausente ou sem tipo editável compatível'
            try:
                option.parse(self.display(on))
                option.parse(self.display(self.GLASS_OFF[name]))
            except ValueError:
                return name+' sem limites compatíveis com o preset'
        return None

    def glass_summary(self,values):
        on=values[self.BLUR] and all(values[name]<1 for name in self.GLASS_ON if name!=self.BLUR)
        label='Ativado' if on else 'Desativado'
        return label, (label+' (blur='+self.display(values[self.BLUR])+
                       ', ativa='+self.display(values['decoration:active_opacity'])+
                       ', inativa='+self.display(values['decoration:inactive_opacity'])+')')

    def sync_blur(self,locked=False):
        issue=self.glass_schema_issue()
        enabled=not issue and self.document is not None and not (locked or self.busy or self.app.busy or self.app.smoke)
        self.blur_box.configure(state='readonly' if enabled else 'disabled')
        if issue:
            self.blur_value.set('')
            self.blur_status.set('Indisponível: '+issue+'. Use o explorador de opções.')
            return
        current={name:self.options[name].current for name in self.GLASS_ON}
        label,summary=self.glass_summary(current)
        status='Atual: '+summary
        if any(name in self.drafts or name in self.staged for name in current):
            try:
                pending={name:self.options[name].parse(self.drafts.get(name,self.display(self.staged.get(name,value))))
                         for name,value in current.items()}
                label,summary=self.glass_summary(pending)
            except ValueError:
                label='';summary='valor inválido'
            status+=' • Pendente: '+summary
        self.blur_value.set(label)
        self.blur_status.set(status)

    def blur_selected(self,event=None):
        if (self.document is None or self.busy or self.app.busy or self.app.smoke or
                str(self.blur_box['state'])=='disabled' or self.glass_schema_issue()):
            self.sync_blur();return
        label=self.blur_value.get()
        if label not in ('Ativado','Desativado'):
            self.sync_blur();return
        values=self.GLASS_ON if label=='Ativado' else self.GLASS_OFF
        changed=any(value!=self.options[name].current for name,value in values.items())
        for name,value in values.items():
            self.staged.pop(name,None)
            if not changed:self.drafts.pop(name,None)
            else:self.drafts[name]=self.display(value)
        if self.selected in values:self._editor_name=None
        self.filter()
        self.status.set('Valores pendentes na memória; use Aplicar e recarregar para revisar e confirmar. Nenhuma alteração aplicada.')

    def _poll_palette(self):
        """Follow the app's cached palette, without IPC or global theme hooks."""
        self._palette_job=None
        spec=getattr(self.app,'palette_spec',None) or {}
        colors=dict(spec.get('colors') or {})
        if colors!=self._palette_colors:
            self._palette_colors=colors
            if colors:
                bg=colors.get('mSurfaceVariant',colors.get('mSurface','#26233a'))
                fg=colors.get('mOnSurface','#e0def4')
                primary=colors.get('mPrimary','#c4a7e7')
                onprimary=colors.get('mOnPrimary',bg)
                self.style.configure('Hyprland.Apply.TButton',background=primary,foreground=onprimary)
                for text in (self.details,self.code):
                    text.configure(background=bg,foreground=fg,insertbackground=fg,
                                   selectbackground=primary,selectforeground=onprimary,
                                   highlightbackground=colors.get('mOutline',bg),
                                   highlightcolor=primary)
                self.style.configure('Hyprland.TNotebook',background=colors.get('mSurface',bg))
                self.style.configure('Hyprland.TNotebook.Tab',background=bg,foreground=fg,padding=(12,6))
                self.style.map('Hyprland.TNotebook.Tab',background=[('selected',primary)],
                               foreground=[('selected',onprimary)])
        self._palette_job=self.app.root.after(250,self._poll_palette)

    def _cancel_palette_poll(self,event):
        if event.widget is self.window and self._palette_job is not None:
            self.app.root.after_cancel(self._palette_job)
            self._palette_job=None

    def alive(self):
        return bool(self.window.winfo_exists())

    def controls(self,busy):
        locked=busy or self.busy or self.app.busy
        for button in (self.apply_button,self.refresh_button):
            button.configure(state='disabled' if locked else 'normal')
        self.code.configure(state='disabled' if locked else 'normal')
        self.sync_blur(locked)
        self.choose()
        if locked:
            self.value_entry.configure(state='disabled');self.bool_box.configure(state='disabled')

    def operation(self,fn,done):
        if self.busy or self.app.busy:
            self.status.set('Aguarde a operação atual.');return
        self.busy=True
        self.controls(True)
        def ready(result,error):
            self.busy=False
            if not self.alive():return
            self.controls(False)
            if error:self.status.set('Falha: '+str(error));return
            done(result)
        self.app.operation(fn,ready)

    def pending(self):
        return bool(self.staged or self.drafts) or (self.document is not None and self.code.get('1.0','end-1c').encode('utf-8')!=self.document.original)

    def load(self):
        if self.busy:return
        if self.pending() and not messagebox.askyesno('Descartar alterações?', 'Reler descarta o texto e todas as alterações ainda não salvas. Continuar?',parent=self.window):return
        def work():
            runtime=self.runtime_factory()
            return runtime,hs.Document(runtime.config),runtime.options()
        def ready(result):
            self.runtime,self.document,options=result
            self.options={option.name:option for option in options};self.staged={};self.saved_values={};self.drafts={};self._editor_name=None
            self.location.set(f'Arquivo: {self.document.path} → {self.document.target}\nCompositor em execução: {self.runtime.binary} • sessão {self.runtime.instance["instance"]}')
            self.code.delete('1.0','end');self.code.insert('1.0',self.document.original.decode('utf-8'));self.code.edit_reset()
            self.category_box.configure(values=['Todas',*sorted({option.category for option in options})])
            if self.category.get() not in self.category_box['values']:self.category.set('Todas')
            self.filter();self.status.set(f'{len(options)} opções nativas carregadas. Edite os valores e use Aplicar e recarregar; nenhuma alteração ocorre antes da confirmação.')
        self.operation(work,ready)

    def filter(self):
        old=self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        term=self.search.get().casefold();category=self.category.get()
        for name,option in self.options.items():
            if category!='Todas' and category!=option.category:continue
            if term not in (name+' '+str(option.raw.get('description',''))).casefold():continue
            self.tree.insert('','end',iid=name,text=name+(' [somente leitura]' if not option.editable else ''),values=(self.display(option.current),self.drafts.get(name,self.display(self.staged[name]) if name in self.staged else '')))
        if old and self.tree.exists(old[0]):self.tree.selection_set(old[0])
        self.choose()
        self.count.set(f'{len(set(self.staged)|set(self.drafts))} alterações pendentes • {len(self.tree.get_children())} opções visíveis / {len(self.options)} disponíveis')
        self.sync_blur()

    @staticmethod
    def display(value):
        return json.dumps(value,ensure_ascii=False) if not isinstance(value,str) else value

    def choose(self,event=None):
        ids=self.tree.selection();self.selected=ids[0] if ids else None
        option=self.options.get(self.selected)
        enabled=option is not None and option.editable and not self.busy and not self.app.busy
        self.value_entry.configure(state='normal' if enabled else 'disabled')
        boolean=option is not None and type(option.current) is bool
        self.bool_box.pack_forget();self.value_entry.pack_forget()
        if boolean:
            self.bool_box.pack(side='left',fill='x',expand=True,padx=5);self.bool_box.configure(state='readonly' if enabled else 'disabled')
        else:self.value_entry.pack(side='left',fill='x',expand=True,padx=5)
        if self._editor_name!=self.selected:
            self._editor_name=self.selected
            self._loading_editor=True
            self.value.set(self.drafts.get(self.selected,self.display(self.staged.get(option.name,option.current))) if option else '')
            self._loading_editor=False
        if boolean:self.bool_value.set('Ativado' if self.value.get()=='true' else 'Desativado')
        if option:
            text=(f'{option.name}\n\n{option.raw.get("description", "Descrição não fornecida")}\n\nTipo observado: {type(option.current).__name__}\nAtual: {self.display(option.current)}\nPadrão: {self.display(option.raw.get("default"))}\nMínimo: {option.raw.get("min")}\nMáximo: {option.raw.get("max")}\nMapa nativo: {self.display(option.raw.get("map"))}\n\n{option.reason}\n\nDados brutos completos:\n'+json.dumps(option.raw,ensure_ascii=False,indent=2))
        else:
            text='Selecione uma opção. As descrições nativas podem estar em inglês. Tipos compostos permanecem somente leitura; o editor avançado permite editar o Lua completo.'
        self.details.configure(state='normal');self.details.delete('1.0','end');self.details.insert('1.0',text);self.details.configure(state='disabled')

    def boolean_selected(self,event=None):
        if self.busy or self.app.busy:return
        self.value.set('true' if self.bool_value.get()=='Ativado' else 'false')

    def value_changed(self,*_):
        if self._loading_editor or self.selected not in self.options:return
        option=self.options[self.selected]
        text=self.value.get()
        if type(option.current) is bool:self.bool_value.set('Ativado' if text=='true' else 'Desativado')
        if text==self.display(self.staged.get(option.name,option.current)):
            self.drafts.pop(option.name,None)
        else:self.drafts[option.name]=text
        if self.tree.exists(option.name):self.tree.set(option.name,'staged',self.drafts.get(option.name,self.display(self.staged[option.name]) if option.name in self.staged else ''))
        self.count.set(f'{len(set(self.staged)|set(self.drafts))} alterações pendentes • {len(self.tree.get_children())} opções visíveis / {len(self.options)} disponíveis')
        self.sync_blur()
        try:option.parse(text)
        except ValueError as exc:self.status.set(f'{option.name}: {exc}');return
        self.status.set('Valor pendente na memória; use Aplicar e recarregar para revisar e confirmar. Nenhuma alteração aplicada.')

    def stage(self):
        if self.busy or self.selected not in self.options:return
        try:value=self.options[self.selected].parse(self.value.get())
        except ValueError as exc:self.status.set(str(exc));return
        self.staged[self.selected]=value
        self.drafts.pop(self.selected,None)
        self.filter();self.status.set('Alteração preparada apenas na memória. Confira o diff ao salvar.')

    def use_default(self):
        if self.selected in self.options:self.value.set(self.display(self.options[self.selected].raw.get('default')))

    def unstage(self):
        if self.busy:return
        self.staged.pop(self.selected,None);self.drafts.pop(self.selected,None);self._editor_name=None;self.filter()

    def proposed(self):
        content=self.code.get('1.0','end-1c').encode('utf-8')
        if self.staged:return hs.managed_config(content,self.staged)
        if hs.BEGIN.encode() in content or hs.END.encode() in content:hs.managed_config(content,{})
        return content

    def confirm_diff(self,diff,apply=False):
        dialog=tk.Toplevel(self.window);dialog.title('Confirmar aplicação — salvar e recarregar' if apply else 'Confirmar gravação persistente — sem recarga');dialog.geometry('1000x650');dialog.transient(self.window)
        warning='Revise o diff completo. Será criado backup do alvo real e validada a sintaxe com luac -p. Isto não executa nem valida a API Lua.'
        if apply:warning+=' ATENÇÃO: confirmar salva e RECARREGA o Lua completo e hooks. Pode iniciar comandos, reiniciar aplicativos e alterar monitores. A recarga automática será desativada somente se necessário antes de salvar. Valores escalares serão conferidos; efeitos personalizados de Lua, regras e hooks NÃO são verificáveis automaticamente. Não há restauração automática da configuração em execução.'
        ttk.Label(dialog,text=warning,wraplength=960,padding=8).pack(fill='x')
        text=tk.Text(dialog,wrap='none',font=('monospace',10));text.insert('1.0',diff);text.configure(state='disabled');scroll=ttk.Scrollbar(dialog,command=text.yview);horizontal=ttk.Scrollbar(dialog,orient='horizontal',command=text.xview);text.configure(yscrollcommand=scroll.set,xscrollcommand=horizontal.set);scroll.pack(side='right',fill='y');horizontal.pack(side='bottom',fill='x');text.pack(fill='both',expand=True)
        result=[False]
        def accept():result[0]=True;dialog.destroy()
        buttons=ttk.Frame(dialog,padding=8);buttons.pack(fill='x');ttk.Button(buttons,text='Cancelar',command=dialog.destroy).pack(side='right');ttk.Button(buttons,text='Confirmar: salvar e recarregar' if apply else 'Confirmar: salvar sem recarregar',command=accept).pack(side='right',padx=8)
        dialog.wait_visibility();dialog.grab_set();self.window.wait_window(dialog)
        return result[0]

    def apply(self):
        if self.app.smoke:self.status.set('Aplicação bloqueada em smoke-test.');return
        if self.busy or self.app.busy or self.document is None:return
        try:
            changes=dict(self.staged)
            for name,text in self.drafts.items():changes[name]=self.options[name].parse(text)
            if self.selected in self.options and self.options[self.selected].editable:
                option=self.options[self.selected]
                value=option.parse(self.value.get())
                if value!=option.current or option.name in changes:changes[option.name]=value
            content=self.code.get('1.0','end-1c').encode('utf-8')
            content=hs.managed_config(content,changes) if changes else self.proposed()
            if hs.BEGIN.encode() in content:
                hs.managed_config(content,{})
                entries=json.loads(content.decode('utf-8').split('-- valores: ',1)[1].splitlines()[0])
                for name,value in entries.items():
                    option=self.options.get(name)
                    if option is None or not option.editable:continue
                    if type(value) is not type(option.current):raise ValueError(f'Valor inválido para {name}: tipo incompatível')
                    option.parse(self.display(value))
                    if value!=option.current or name in changes:changes[name]=value
            diff=self.document.diff(content)
        except Exception as exc:self.status.set('Falha: '+str(exc));return
        if not diff and not changes:self.status.set('Nenhuma alteração para aplicar.');return
        self.busy=True;self.controls(True)
        try:confirmed=self.confirm_diff(diff,apply=True)
        finally:
            self.busy=False;self.controls(False)
        if not confirmed:self.status.set('Aplicação cancelada. Nada foi alterado.');return
        def ready(result):
            if result['saved']:
                self.saved_values.update(changes)
                self.code.delete('1.0','end');self.code.insert('1.0',content.decode('utf-8'));self.code.edit_reset()
            if not result['verified']:
                self.staged.update(changes)
                self.filter()
                self.status.set(('Salvo, mas aplicação NÃO confirmada. ' if result['saved'] else 'Não salvo; aplicação interrompida. ')+str(result['error'])+f" Backup: {result['backup']}. Nenhuma restauração automática do Lua em execução.")
                return
            for name,value in result['observed'].items():
                self.options[name].current=value;self.options[name].raw['current']=value
            self.staged.clear();self.drafts.clear();self._editor_name=None;self.filter()
            self.status.set(f"Salvo e recarregado; {len(changes)} valores escalares verificados e tabela atualizada. Backup: {result['backup']}. Efeitos personalizados de Lua/hooks não verificáveis automaticamente.")
        self.operation(lambda:hs.apply_changes(self.runtime,self.document,content,changes),ready)

    def prepare_save(self):
        if self.app.smoke:self.status.set('Preparação bloqueada em smoke-test.');return
        if self.busy or self.app.busy or self.runtime is None:return
        if not messagebox.askyesno('Desativar recarga automática nesta sessão?', 'Para garantir que salvar não execute hooks, esta ação altera SOMENTE misc.disable_autoreload para true no compositor em execução, com verificação por leitura. Não grava arquivo nem recarrega. Alterações externas ao arquivo também deixarão de recarregar automaticamente até uma recarga/reinício ou mudança explícita dessa opção. Deseja desativar?',parent=self.window):return
        def ready(_):self.status.set('Recarga automática desativada e verificada nesta sessão. Agora é possível salvar sem recarregar. Use Recarregar Hyprland explicitamente quando desejar executar o Lua salvo.')
        self.operation(self.runtime.disable_autoreload,ready)

    def save(self):
        if self.app.smoke:self.status.set('Gravação bloqueada em smoke-test.');return
        if self.busy or self.document is None:return
        try:
            content=self.proposed();diff=self.document.diff(content)
        except Exception as exc:self.status.set('Falha: '+str(exc));return
        if not diff:self.status.set('Nenhuma alteração para salvar.');return
        if not self.confirm_diff(diff):self.status.set('Gravação cancelada. Nada foi alterado.');return
        staged=dict(self.staged)
        def work():
            self.runtime.ensure_save_safe()
            return self.document.save(content)
        def ready(backup):
            self.saved_values.update(staged);self.staged.clear()
            self.code.delete('1.0','end');self.code.insert('1.0',content.decode('utf-8'));self.code.edit_reset();self.filter()
            self.status.set(f'Salvo e relido: {self.document.target}. Backup: {backup}. Nenhuma recarga solicitada. Valores em execução podem continuar antigos.')
        self.operation(work,ready)

    def reload(self):
        if self.app.smoke:self.status.set('Recarga bloqueada em smoke-test.');return
        if self.busy or self.runtime is None:return
        if not messagebox.askyesno('Executar configuração Lua e hooks?', 'Recarregar executa o Lua salvo completo e hooks de recarga. Pode iniciar comandos, alterar monitores, atalhos e temas ou reiniciar aplicativos conforme sua configuração. Alterações não salvas NÃO serão usadas. Continuar?',parent=self.window):return
        def ready(result):self.status.set('Recarga solicitada; sem erros de configuração reportados. Use Conferir valores em execução para verificação; isso não prova efeitos de regras/atalhos.')
        self.operation(self.runtime.reload,ready)

    def readback(self):
        if self.busy or self.runtime is None:return
        names=list(dict.fromkeys([*self.saved_values,*self.staged,*([self.selected] if self.selected else [])]))
        if not names:self.status.set('Selecione uma opção ou salve alterações para conferir valores.');return
        def ready(result):
            lines=[]
            for name,raw in result.items():
                expected=self.saved_values.get(name)
                observed=next((raw[key] for key in ('bool','int','float','str','css','vec2','custom') if key in raw),None)
                verdict=(' • corresponde ao salvo' if observed==expected and name in self.saved_values else ' • divergente/representação nativa diferente' if name in self.saved_values else '')
                lines.append(name+': '+self.display(raw)+verdict)
            self.details.configure(state='normal');self.details.delete('1.0','end');self.details.insert('1.0','Leitura de execução (sem modificar o compositor):\n\n'+'\n\n'.join(lines));self.details.configure(state='disabled');self.status.set('Valores em execução relidos. Salvar não significa aplicar em execução.')
        self.operation(lambda:self.runtime.readback(names),ready)

    def close(self):
        if self.busy:self.status.set('Aguarde a operação antes de fechar.');return
        if self.pending() and not messagebox.askyesno('Descartar alterações?', 'Fechar sem salvar as alterações preparadas?',parent=self.window):return
        self.window.destroy()
