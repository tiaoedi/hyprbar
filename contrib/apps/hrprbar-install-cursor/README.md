# hrprbar-install cursor

Aplicativo nativo Python/Tkinter para visualizar, instalar e trocar temas locais de cursor. Não instala dependências do sistema, não cria serviços e **não modifica o cursor ao abrir, selecionar um tema, mudar tamanho ou executar testes**. Nome solicitado preservado literalmente: `hrprbar-install cursor`.

## Abrir

```sh
./contrib/apps/hrprbar-install-cursor/run.sh
```

Execute a partir da raiz do repositório. Requer Linux, Python 3.10+, Tkinter, Pillow, libXcursor e uma sessão X11/XWayland para a interface. `PYTHON=/caminho/do/python ./contrib/apps/hrprbar-install-cursor/run.sh` seleciona outro interpretador. O lançador verifica dependências, sem instalar pacotes. Para aplicar são necessários Hyprland com configuração Lua, GSettings, xrdb e D-Bus/systemd do usuário.

Este diretório contém um aplicativo auxiliar independente, não um painel nativo nem um plugin do núcleo do Hyprbar. Não participa da compilação C++/Meson e não é instalado pelo instalador principal. Não inclui temas de cursor de terceiros: lê temas locais e permite baixar pacotes das fontes configuradas por ação explícita. Licença MIT do repositório.

## Recuperar depois de formatar

O código da central, dos gerenciadores de cursores/ícones e os testes ficam neste diretório do repositório `tiaoedi/hyprbar`, branch `main`. Em uma instalação nova, com Git e as dependências acima disponíveis:

```sh
git clone --branch main https://github.com/tiaoedi/hyprbar.git
cd hyprbar
./contrib/apps/hrprbar-install-cursor/run-settings.sh
# Para abrir somente os cursores:
./contrib/apps/hrprbar-install-cursor/run.sh
```

Os lançadores são portáteis: usam `python3` ou o interpretador indicado por `PYTHON`, sem caminhos pessoais nem dependência do Hermes. Para editar/aplicar Lua pela central também é necessário `luac` compatível no PATH para a validação sintática. Para prévias SVG de ícones, librsvg/Cairo são opcionais; os demais formatos não dependem deles. O clone não instala pacotes, não cria atalhos no menu e não aplica configurações automaticamente.

**Este repositório preserva o programa, não um backup do desktop.** Antes de formatar, copie separadamente os temas baixados (`~/.local/share/icons` ou `$XDG_DATA_HOME/icons`, e `~/.icons`), as configurações pessoais do Hyprland/GTK e os backups que quiser manter. Esses arquivos pessoais não são publicados junto ao código.

## Central de configurações do Hyprland

A nova entrada **Configurações do Hyprland** (`hrprbar-config`) abre a página inicial da central, com módulos de **Hyprland**, **Temas de ícones…** e **Cursores**. A entrada original `hrprbar-install cursor` continua compatível. No código portátil, execute `./run-settings.sh` neste diretório (ou `./contrib/apps/hrprbar-install-cursor/run-settings.sh` na raiz do repositório), usando `PYTHON` para escolher o interpretador existente. Não instala dependências, serviços ou substitui o painel próprio do Hyprbar.

**Configurar Hyprland…** consulta as opções expostas pela versão realmente em execução, com categorias, busca, valor atual, padrão e limites. Booleanos usam **Ativado/Desativado**, sem exigir digitar `true`/`false`. **Aplicar e recarregar** inclui o valor atual do editor mesmo sem preparar manualmente, mostra o diff e pede confirmação para salvar e recarregar o Lua completo. Após a recarga, relê os valores escalares e só confirma aplicação quando correspondem ao solicitado. Falhas distinguem arquivo salvo de valor aplicado; efeitos arbitrários de código Lua não são comprovados por essa leitura. Alterações ficam pendentes até confirmação. O editor Lua avançado permite editar a configuração completa — incluindo monitores, atalhos, regras, animações e inicialização — sem afirmar que todos esses recursos têm formulários dedicados. Código Lua pode executar comandos ao ser carregado: revise o diff. A validação sintática não prova que as opções ou regras funcionarão em runtime.

A interface apresenta uma única ação de configuração: **Aplicar e recarregar**. O valor editado entra na proposta sem exigir outro botão de preparação. Após revisar e confirmar o diff, a operação identifica o alvo ativo, protege contra alterações concorrentes, prepara a gravação segura, cria backup, grava, recarrega e verifica os valores. A confirmação alerta que o Lua e seus hooks serão executados; erros não são apresentados como aplicação concluída. A opção de provocar crash manual permanece bloqueada no formulário.

## Aparência do Hyprbar

A interface consulta `hyprbar msg color-scheme-get` e `hyprbar msg theme-mode-get`, somente leitura, com timeout. Para paletas comunitárias, carrega a variante claro/escuro de `$XDG_STATE_HOME/hyprbar/community-palettes/<nome codificado na URL>.json` (padrão `~/.local/state`). Atualmente acompanha **Rose Pine Alt • escuro**: fundo `#191724`, painéis `#26233a`, seleção/foco `#c4a7e7` e texto `#e0def4`. Atualiza ao receber foco e a cada cinco segundos dentro da própria interface, sem daemon, hooks, reload global nem alterações ao Hyprbar. Se a origem não estiver disponível, uma paleta de reserva é explicitamente indicada. Usa fonte Hyprbar tamanho 11 se disponível ao Tk; caso contrário Liberation Sans instalada. Prévias usam quadriculado neutro para evidenciar transparência.

## Usar

- A lista mostra todos os temas de cursor encontrados e miniaturas reais do ponteiro. Busca por nome. Precedência: `~/.icons`, `$XDG_DATA_HOME/icons` (padrão `~/.local/share/icons`), demais diretórios XDG, `/usr/share/icons`. Duplicatas pelo identificador exato são ocultadas; nomes com maiúsculas diferentes são distintos no Linux. Temas só de ícones não aparecem.
- Selecione um tema para ver oito desenhos carregados diretamente por `libXcursor` via `ctypes`; não são ícones ilustrativos. Animações mostram o primeiro quadro. Fundo quadriculado revela transparência. Imagens grandes podem ser reduzidas apenas na prévia para caber; dimensões e tamanho nominal originais estão escritos.
- O seletor oferece tamanhos realmente presentes no arquivo `left_ptr`. Solicitações não exatas são ajustadas ao tamanho disponível mais próximo (empate: menor). Cada desenho também informa seus próprios tamanhos e a escolha real da biblioteca. Não há promessa de que um nominal 40 resulte em imagem 40: este tema macOS27 tem 24, 32, 48, 64 e 96. Desenhos diferentes podem ter conjuntos diferentes e recebem aviso explícito.
- Somente **Aplicar tema**, após confirmação, grava configurações. Temas apenas Hyprcursor são identificados, mas não têm prévia nem aplicação unificada: GTK/XWayland precisam de Xcursor.
- **Instalar novo: arquivo…** aceita ZIP, TAR e variantes comprimidas (`tar.gz`, `tgz`, `tar.xz`, `tar.bz2`, etc.); **Instalar novo: pasta…** aceita uma pasta de tema ou coleção. Todos os temas reais encontrados (`cursors/` ou `manifest.hl`) são instalados e listados ao concluir em `$XDG_DATA_HOME/icons`. Nenhum é aplicado automaticamente.

## Baixar temas pela interface

O botão **Baixar temas…** abre o catálogo já configurado em **Todos os repositórios**. As nove fontes abaixo estão configuradas sem ajuste manual; **Buscar versões/temas** consulta em paralelo a última release publicada de cada uma. Abrir o aplicativo ou o diálogo não inicia acesso à internet. Uma fonte indisponível não descarta os resultados das demais: o estado/erro de cada repositório aparece abaixo da lista.

| Família | Repositório GitHub |
| --- | --- |
| Bibata | `ful1e5/Bibata_Cursor` |
| BreezeX | `ful1e5/BreezeX_Cursor` |
| GoogleDot | `ful1e5/Google_Cursor` |
| macOS | `ful1e5/apple_cursor` |
| Fuchsia | `ful1e5/fuchsia-cursor` |
| Banana | `ful1e5/banana-cursor` |
| Notwaita | `ful1e5/notwaita-cursor` |
| Phinger | `phisch/phinger-cursors` |
| Rosé Pine | `rose-pine/cursors` |

1. Use **Buscar versões/temas** para carregar todas as fontes, ou selecione uma família. O campo editável também aceita `owner/repo` ou `https://github.com/owner/repo`; editar esse campo muda para **Personalizado**.
2. Filtre variantes por nome, versão ou origem. Cada linha mostra pacote, tamanho comprimido, versão e repositório. Selecione para ver a URL de origem e se há SHA256 publicado. Arquivos de coleção podem instalar vários temas, não apenas a variante individual.
3. Clique em **Baixar e instalar** e confirme o pacote/destino. O download e a validação rodam em segundo plano, sem bloquear a interface; operações simultâneas são impedidas. Erros de conexão, tempo esgotado, limite da API, ausência de release e tema já instalado aparecem no próprio diálogo. É possível tentar novamente; temas existentes não são substituídos.
4. O destino é `$XDG_DATA_HOME/icons` (padrão `~/.local/share/icons`). Após instalar, a lista local é atualizada: um tema único é selecionado para prévia; uma coleção exige escolher um tema na lista principal. **Nada é aplicado automaticamente.** Confira o tamanho real disponível, clique em **Aplicar tema** e confirme para usar o fluxo existente de backups/verificação. Não é necessário configurar manualmente arquivos para baixar temas.

**Escopo das fontes:** somente assets de GitHub Releases em `tar.xz`, `tar.gz`, `tar.bz2`, `tgz` ou `txz`, com temas empacotados. ZIPs (incluindo variantes Windows e bitmaps) e arquivos de código-fonte não são oferecidos. Extensão permitida não comprova que o pacote contém um tema: o instalador exige conteúdo válido antes de publicar. Não clona repositórios, não instala a partir da árvore de fontes e nunca executa scripts/instaladores baixados. Licenças dos temas continuam sendo as dos respectivos autores.

**Rede e integridade:** `urllib` da biblioteca padrão, timeout de conexão/leitura de 20 s, metadados até 2 MiB e download até 64 MiB; tamanho recebido deve conferir com o catálogo. A URL inicial precisa pertencer ao repositório/release informado em `github.com`; só redirecionamentos HTTPS para esse caminho ou `release-assets.githubusercontent.com` são aceitos, verificados antes de seguir. URLs com credenciais/portas explícitas e destinos arbitrários/locais são recusados. SHA256 é conferido quando o GitHub o publica; quando ausente isso é indicado. HTTPS e hash publicado não equivalem a assinatura do autor. Downloads temporários são removidos tanto no sucesso como na falha. A extração mantém todos os limites abaixo, por isso coleções grandes/altamente comprimidas podem ser recusadas — prefira uma variante individual.

Os testes automatizados do catálogo usam respostas controladas e imagens Xcursor geradas, sem internet, instalação no desktop real ou aplicação runtime. Referência da API: documentação oficial GitHub, `https://docs.github.com/en/rest/releases/releases#get-the-latest-release` e `https://docs.github.com/en/rest/releases/assets`.

## Temas de ícones

**Temas de ícones…** abre um gerenciador separado da lista de cursores. Mostra temas locais válidos e prévias reais PNG/SVG/XPM, busca, instalação de arquivo/pasta e **Baixar ícones — GitHub…**. Fontes configuradas: `zayronxio/Zafiro-icons` (Zafiro), `thissayantan/frost-icon-theme` (Frost) e `niraletter/full-icon-themes` (coleções, como Dracula). O campo aceita outro repositório `owner/repo`. Consultar e baixar exigem clique explícito; instalações vão para `$XDG_DATA_HOME/icons` e não aplicam automaticamente.

O instalador exige `index.theme`, metadados e imagens reais, rejeita diretórios/links que escapem do tema e mantém os mesmos limites de extração e download. Coleções só são publicadas após validação; temas existentes nunca são substituídos. Coleções grandes podem exceder limites e dependências por symlinks entre temas são recusadas.

**Aplicar ícones…** exige confirmação, preserva as demais chaves e os links simbólicos GTK3/4, salva backups dos alvos reais e do valor GSettings anterior, altera somente `gtk-icon-theme-name` / `org.gnome.desktop.interface icon-theme` e verifica a leitura posterior. Falhas tentam restaurar os valores anteriores e informam falhas de restauração. Não muda cursores nem recarrega compositor/barra; Qt, sandboxes e aplicativos com tema próprio podem ignorar os valores GTK. Prévia SVG usa librsvg/Cairo já disponíveis; sem eles, a interface informa a limitação sem instalar dependências.

## Catálogos externos: Flaticon, Custom Cursor e GNOME-Look

O catálogo de cursores também oferece atalhos explícitos para `https://www.flaticon.com/br/icones-gratis/cursor`,  `https://custom-cursor.com/es/top-downloaded-cursors` e `https://www.gnome-look.org/browse?cat=132&ord=latest`. Eles abrem no navegador somente ao clicar. São fontes externas, não repositórios de pacotes Xcursor validados: imagens, extensões e formatos de outras plataformas não se tornam temas do Hyprland automaticamente. Verifique licença, atribuição e compatibilidade no site. O aplicativo não contorna login, bloqueios ou pagamentos e não executa instaladores desses sites.

## Compatibilidade XCB e Android Emulator

Em cada **Aplicar tema**, o gerenciador também atualiza o fallback `~/.icons/default/index.theme` com backup e leitura posterior, preservando metadados alheios. Quando necessário, cria um alias `~/.icons/<tema>` sem substituir diretórios/links existentes. Conflitos são recusados. O fluxo já atualiza `Xcursor.theme` e `Xcursor.size` no Xresources runtime.

Isso cobre loaders antigos que ignoram `XCURSOR_THEME` ou não procuram no diretório XDG. No Android Emulator 37.2.12 deste host, a biblioteca Qt/XCB carregava hyprbar apesar do ambiente macOS; o mesmo loader, testado sem mover o mouse, passou a abrir macOS/left_ptr após alinhar fallback/alias/Xresources. O Android e o AVD não foram modificados. Esse teste prova resolução do arquivo, não que todo aplicativo já aberto descartou seu cache. Aplicativos que desenham cursores próprios ou mantêm caches continuam com ressalvas; não há reinício automático.

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

Valida em diretório privado no mesmo filesystem do destino antes de instalar. Diretórios de tema são publicados com `renameat2(RENAME_NOREPLACE)` do Linux, sem sobrescrever nem em colisão concorrente. Uma coleção é pré-validada inteira; falha na publicação tenta remover só os temas novos daquela operação. Não é uma transação global atômica entre vários diretórios. A validação não substitui confiança na origem: não há antivírus; acesso à rede e download dependem de ação explícita.

## Testes e diagnóstico (somente leitura no desktop)

```sh
cd contrib/apps/hrprbar-install-cursor
./run.sh --list
./run.sh --smoke-test
python3 -m unittest -v
```

`--list` retorna JSON. `--smoke-test` constrói a interface, inspeciona widgets, renderiza amostras reais e fecha automaticamente sem aplicar. Precisa do DISPLAY da sessão e de pelo menos um tema Xcursor instalado. O teste GUI é ignorado quando não há DISPLAY. Os testes unitários de arquivos usam imagens sintéticas de teste, sem exigir um tema específico instalado; instalação/persistência usam diretórios temporários isolados em `$TMPDIR` (ou `~/.cache/hrprbar-install-cursor/tests`), nunca a configuração ativa. Testes não executam comandos de aplicação runtime ou reabertura de aplicativos.

APIs de referência: documentação oficial Hyprland “Using hyprctl” (`https://wiki.hypr.land/configuring/core/advanced-configuration/using-hyprctl/`) e “Config options” (`https://wiki.hypr.land/configuring/core/config-options/`), com `setcursor` e `cursor.enable_hyprcursor`. A integração é voltada à configuração Lua `~/.config/hypr/hyprland.lua`, não migra automaticamente configurações Hyprland antigas em outra sintaxe. Leitura da API local 0.57.2 verificada; compatibilidade com outras versões precisa de verificação.
