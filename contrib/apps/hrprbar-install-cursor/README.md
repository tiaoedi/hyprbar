# hrprbar-install cursor

Aplicativo nativo Python/Tkinter para visualizar, instalar e trocar temas locais de cursor. Não instala pacotes, não cria serviços e **não modifica o cursor ao abrir, selecionar um tema, mudar tamanho ou executar testes**. Nome solicitado preservado literalmente: `hrprbar-install cursor`.

## Abrir

```sh
./contrib/apps/hrprbar-install-cursor/run.sh
```

Execute a partir da raiz do repositório. Requer Linux, Python 3.10+, Tkinter, Pillow, libXcursor e uma sessão X11/XWayland para a interface. `PYTHON=/caminho/do/python ./contrib/apps/hrprbar-install-cursor/run.sh` seleciona outro interpretador. O lançador verifica dependências, sem instalar pacotes. Para aplicar são necessários Hyprland com configuração Lua, GSettings, xrdb e D-Bus/systemd do usuário.

Este diretório contém um aplicativo auxiliar independente, não um painel nativo nem um plugin do núcleo do Hyprbar. Não participa da compilação C++/Meson e não é instalado pelo instalador principal. Não inclui temas de cursor de terceiros: lê os temas locais existentes. Licença MIT do repositório.

## Aparência do Hyprbar

A interface consulta `hyprbar msg color-scheme-get` e `hyprbar msg theme-mode-get`, somente leitura, com timeout. Para paletas comunitárias, carrega a variante claro/escuro de `$XDG_STATE_HOME/hyprbar/community-palettes/<nome codificado na URL>.json` (padrão `~/.local/state`). Atualmente acompanha **Rose Pine Alt • escuro**: fundo `#191724`, painéis `#26233a`, seleção/foco `#c4a7e7` e texto `#e0def4`. Atualiza ao receber foco e a cada cinco segundos dentro da própria interface, sem daemon, hooks, reload global nem alterações ao Hyprbar. Se a origem não estiver disponível, uma paleta de reserva é explicitamente indicada. Usa fonte Hyprbar tamanho 11 se disponível ao Tk; caso contrário Liberation Sans instalada. Prévias usam quadriculado neutro para evidenciar transparência.

## Usar

- A lista mostra todos os temas de cursor encontrados e miniaturas reais do ponteiro. Busca por nome. Precedência: `~/.icons`, `$XDG_DATA_HOME/icons` (padrão `~/.local/share/icons`), demais diretórios XDG, `/usr/share/icons`. Duplicatas pelo identificador exato são ocultadas; nomes com maiúsculas diferentes são distintos no Linux. Temas só de ícones não aparecem.
- Selecione um tema para ver oito desenhos carregados diretamente por `libXcursor` via `ctypes`; não são ícones ilustrativos. Animações mostram o primeiro quadro. Fundo quadriculado revela transparência. Imagens grandes podem ser reduzidas apenas na prévia para caber; dimensões e tamanho nominal originais estão escritos.
- O seletor oferece tamanhos realmente presentes no arquivo `left_ptr`. Solicitações não exatas são ajustadas ao tamanho disponível mais próximo (empate: menor). Cada desenho também informa seus próprios tamanhos e a escolha real da biblioteca. Não há promessa de que um nominal 40 resulte em imagem 40: este tema macOS27 tem 24, 32, 48, 64 e 96. Desenhos diferentes podem ter conjuntos diferentes e recebem aviso explícito.
- Somente **Aplicar tema**, após confirmação, grava configurações. Temas apenas Hyprcursor são identificados, mas não têm prévia nem aplicação unificada: GTK/XWayland precisam de Xcursor.
- **Instalar novo: arquivo…** aceita ZIP, TAR e variantes comprimidas (`tar.gz`, `tgz`, `tar.xz`, `tar.bz2`, etc.); **Instalar novo: pasta…** aceita uma pasta de tema ou coleção. Todos os temas reais encontrados (`cursors/` ou `manifest.hl`) são instalados e listados ao concluir em `$XDG_DATA_HOME/icons`. Nenhum é aplicado automaticamente.

## Aplicação, backups e limites reais

Na aplicação Xcursor, a ferramenta preserva o mesmo desenho de origem no compositor e nos consumidores Xcursor, desativa o caminho Hyprcursor e sincroniza:

1. Arquivo **ativo** `~/.config/hypr/hyprland.lua` (ou `$XDG_CONFIG_HOME/hypr/hyprland.lua`), resolvendo links simbólicos para editar o alvo real. Atualiza apenas `hl.env` para XCURSOR/HYPRCURSOR THEME/SIZE e a opção `enable_hyprcursor=false`; não altera hardware cursor, monitores, atalhos ou aplicativos.
2. GTK3/GTK4 `settings.ini`: mantém outras seções/chaves usando ConfigParser. Comentários e formatação podem ser normalizados.
3. GSettings `org.gnome.desktop.interface` cursor-theme e cursor-size.
4. Bloco identificado em `~/.Xresources`, preservando o restante, e `xrdb -merge` em runtime.
5. Ambiente de ativação D-Bus/systemd (`dbus-update-activation-environment --systemd`).
6. `hyprctl reload` e `hyprctl setcursor`.

Cada arquivo existente recebe uma cópia exata ao lado, sufixo `.bak-<identificador único>`, **antes** de ser escrito. O link da configuração Hyprland é mantido, e o backup fica ao lado do alvo real. Arquivos são gravados por substituição atômica e relidos; falha durante a etapa de arquivos tenta restaurar o estado anterior. Uma falha em comandos posteriores pode deixar aplicação parcial: o relatório identifica falhas e não promete rollback do ambiente da sessão. Backups não são apagados automaticamente. Para desfazer, escolha o backup correto e restaure-o sobre seu alvo, depois recarregue conforme apropriado; arquivos que não existiam antes não têm backup.

O relatório faz leitura posterior de GSettings, Xresources, ambiente systemd, opção `enable_hyprcursor`, erros de configuração e escalas dos monitores. Aceitação de `setcursor` não é prova visual, e o ambiente de ativação D-Bus não tem leitura universal equivalente. Escalas diferentes podem produzir dimensões físicas diferentes mesmo com nominal igual. Sandboxes, temas próprios e toolkits com cache podem ignorar valores do host.

**Não existe garantia segura de trocar imediatamente o cursor em todos os aplicativos já abertos.** A ferramenta não mata aplicativos, não reinicia navegador nem encerra a sessão automaticamente. Após aplicar, o relatório lista somente PID, executável e as duas variáveis XCURSOR relevantes dos clientes visíveis cujo ambiente diverge. Não expõe outros dados do processo. Ambiente antigo/ausente não prova cache incorreto; ambiente igual não prova desenho atualizado.

**Reabrir aplicativos…** é opcional. Exige selecionar um aplicativo e uma segunda confirmação com aviso de perda de formulários/janelas privadas/trabalho não salvo. Apenas processos principais de navegadores Chromium nativos compatíveis podem ser reabertos de forma assistida. Mantém argumentos, diretório de trabalho e ambiente em memória, atualiza as quatro variáveis de cursor e solicita `--restore-last-session`. Nunca força SIGKILL; se não encerrar, pede reabertura manual. Restauração das abas não é garantida. Processos auxiliares, Flatpak/Snap e outros aplicativos devem ser reabertos manualmente. Essa ação deliberadamente não é exercitada nos testes.

## Segurança da instalação

Extração manual, sem `extractall`. Rejeita caminhos absolutos, `..`, barras invertidas, tipos especiais, hardlinks, entradas duplicadas, links externos/quebrados/circulares e aliases que dependem de outro tema. Links simbólicos relativos internos válidos são preservados e só criados após os arquivos regulares. Limites: 20 mil entradas, 256 MiB totais, 16 MiB por arquivo, razão máxima 200:1. Temas Xcursor precisam de ao menos uma imagem decodificável; Hyprcursor requer manifesto não vazio, mas a ferramenta não valida integralmente esse formato nativo. Pacotes legítimos extremamente comprimidos podem ser recusados por segurança.

Valida em diretório privado no mesmo filesystem do destino antes de instalar. Diretórios de tema são publicados com `renameat2(RENAME_NOREPLACE)` do Linux, sem sobrescrever nem em colisão concorrente. Uma coleção é pré-validada inteira; falha na publicação tenta remover só os temas novos daquela operação. Não é uma transação global atômica entre vários diretórios. A validação não substitui confiança na origem: não há antivírus nem download automático.

## Testes e diagnóstico (somente leitura no desktop)

```sh
cd contrib/apps/hrprbar-install-cursor
./run.sh --list
./run.sh --smoke-test
python3 -m unittest -v
```

`--list` retorna JSON. `--smoke-test` constrói a interface, inspeciona widgets, renderiza amostras reais e fecha automaticamente sem aplicar. Precisa do DISPLAY da sessão e de pelo menos um tema Xcursor instalado. O teste GUI é ignorado quando não há DISPLAY. Os testes unitários de arquivos usam imagens sintéticas de teste, sem exigir um tema específico instalado; instalação/persistência usam diretórios temporários isolados em `$TMPDIR` (ou `~/.cache/hrprbar-install-cursor/tests`), nunca a configuração ativa. Testes não executam comandos de aplicação runtime ou reabertura de aplicativos.

APIs de referência: documentação oficial Hyprland “Using hyprctl” (`https://wiki.hypr.land/configuring/core/advanced-configuration/using-hyprctl/`) e “Config options” (`https://wiki.hypr.land/configuring/core/config-options/`), com `setcursor` e `cursor.enable_hyprcursor`. A integração é voltada à configuração Lua `~/.config/hypr/hyprland.lua`, não migra automaticamente configurações Hyprland antigas em outra sintaxe. Leitura da API local 0.57.2 verificada; compatibilidade com outras versões precisa de verificação.
