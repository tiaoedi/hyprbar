# Instalar o Hyprbar e seus aplicativos auxiliares em outro PC

Este guia reúne a instalação do Hyprbar e dos auxiliares distribuídos neste repositório. Não é um backup do computador nem um instalador de todos os programas pessoais. O Hyprbar é um fork independente baseado no Noctalia v5.2.1.

## 1. Preparar o sistema e baixar uma única vez

Use uma sessão Linux Wayland compatível, com EGL/GLES. A compilação e os testes do fork foram verificados originalmente no Fedora 44 x86_64; isso não comprova compatibilidade com qualquer versão/distribuição. O compositor, seus drivers e a sessão gráfica precisam estar instalados separadamente.

Instale Git e as dependências de compilação da sua distribuição conforme [`BUILDING.md`](BUILDING.md). No Fedora, o bloco `sudo dnf install ...` está na seção **Fedora** desse arquivo. Os comandos com `sudo` exigem autorização do administrador; não execute o clone ou os aplicativos como root.

```sh
git clone --branch main https://github.com/tiaoedi/hyprbar.git
cd hyprbar
```

Todos os comandos seguintes partem da raiz desse clone, salvo indicação contrária. Se já clonou, use a pasta existente; não repita o clone nem substitua arquivos locais. Antes de atualizar com `git pull --ff-only`, revise `git status` e preserve suas modificações.

## 2. Instalar o Hyprbar e os dois plugins próprios

Com as dependências de compilação disponíveis:

```sh
./tools/install-with-community-plugins.sh
```

O script executa `just configure release`, `just build release` e `sudo just install release`, e copia os plugins **calculator** e **wellbeing** para `${XDG_DATA_HOME:-$HOME/.local/share}/hyprbar/plugins/`. Recusa destinos de plugins já existentes antes de compilar; não apague esses destinos para repetir a instalação sem antes revisar e fazer backup. Não instala dependências, não ativa plugins e não instala os aplicativos auxiliares descritos abaixo.

Para instalar somente o núcleo, em vez do script:

```sh
just configure release
just build release
sudo just install release
```

Para iniciar na sessão Wayland atual:

```sh
hyprbar --daemon
```

Não inicie uma segunda instância se a barra já estiver ativa. Com o Hyprbar em execução, ative os plugins próprios se desejar:

```sh
hyprbar msg plugins enable tiaoedi/calculator
hyprbar msg plugins enable tiaoedi/wellbeing
```

Os atalhos opcionais e configurações pessoais não são aplicados pelo script. Plugins de outras fontes são gerenciados separadamente em **Configurações → Plugins**, respeitando os requisitos de API/compatibilidade; não são todos instalados ou ativados por esse comando.

### Iniciar junto com a sessão

Adicione uma única inicialização à configuração do compositor. No Hyprland com configuração INI tradicional:

```ini
exec-once = hyprbar --daemon
```

Esse exemplo é INI: não cole essa linha dentro de um arquivo Lua. Se seu Hyprland usa Lua, use o mecanismo de inicialização suportado pela versão instalada, sem sobrescrever a configuração existente. Para Niri consulte [`docs/user/compositor-settings/niri.mdx`](docs/user/compositor-settings/niri.mdx). Nenhum dos passos deste guia cria automaticamente um serviço systemd ou configura o autostart.

## 3. Central, gerenciador de cursores e gerenciador de ícones

São módulos do mesmo aplicativo auxiliar Python/Tkinter, em [`contrib/apps/hrprbar-install-cursor/`](contrib/apps/hrprbar-install-cursor/), não três instalações independentes. Não participam da compilação C++ e não são instalados pelo script do núcleo.

Dependências: Python 3.10+, Tkinter, Pillow e libXcursor. A interface precisa de uma sessão X11/XWayland; o módulo Hyprland requer `hyprctl`, configuração Lua compatível e `luac` no PATH. A aplicação de cursores também usa GSettings, `xrdb` e D-Bus/systemd do usuário. As prévias SVG de ícones usam librsvg/Cairo quando disponíveis. A descoberta segura de ícones requer Linux 5.6+ e uma libc que exponha `openat2`; ter somente o kernel adequado não garante esse suporte.

No Fedora, os pacotes principais da interface podem ser instalados assim (isso não instala o compositor nem configura a sessão):

```sh
sudo dnf install python3 python3-tkinter python3-pillow libXcursor
```

Confira o interpretador antes de abrir:

```sh
python3 -c 'import tkinter, PIL, ctypes.util; assert ctypes.util.find_library("Xcursor"), "libXcursor ausente"; print("Dependências Python/Xcursor disponíveis")'
```

Abra a central:

```sh
./contrib/apps/hrprbar-install-cursor/run-settings.sh
```

Na central, escolha:

- **Configurar Hyprland…**: opções da versão em execução, efeito de vidro e editor Lua avançado. A aplicação exige revisão do diff e confirmação, com backups.
- **Temas de ícones…**: lista, prévias, instalação local e catálogos. Aplicar ícones é uma ação separada de instalar.
- **Cursores**: prévias reais, seleção de tamanho, instalação e aplicação confirmada.

Para abrir somente os cursores:

```sh
./contrib/apps/hrprbar-install-cursor/run.sh
```

Se usar outro Python já preparado, indique `PYTHON=/caminho/do/python` antes de um desses comandos. Os lançadores verificam dependências e não instalam pacotes. Mantenha o clone no disco: esses comandos executam os arquivos dele. Não recriam automaticamente os atalhos locais `hrprbar-config`, `hrprbar-install-cursor` ou as entradas do menu do computador antigo.

Detalhes de uso, segurança, requisitos e limites: [`contrib/apps/hrprbar-install-cursor/README.md`](contrib/apps/hrprbar-install-cursor/README.md).

## 4. Instalar o tema de cursor hyprbar-1

O tema está incluído no Git, com Xcursor, Hyprcursor, licença, fontes SVG e prévia. Na raiz do clone:

```sh
mkdir -p "$HOME/.local/share/icons"
if [ -e "$HOME/.local/share/icons/hyprbar-1" ] || [ -L "$HOME/.local/share/icons/hyprbar-1" ]; then
    printf '%s\n' 'hyprbar-1 já existe; nenhuma cópia foi realizada.'
else
    cp -aT --no-clobber tools/hyprbar-cursors/hyprbar-1 "$HOME/.local/share/icons/hyprbar-1"
fi
```

Depois selecione **hyprbar-1** no gerenciador de cursores e escolha **28 px** para reproduzir o tamanho usado neste ambiente. Também estão disponíveis 24, 32, 40, 48 e 64 px. Copiar não ativa o tema. Não use `sudo`. Aplicativos já abertos podem manter caches e precisar de reabertura manual.

O tema original `hyprbar` também está em `tools/hyprbar-cursors/hyprbar/`; não o confunda com o tema de ícones de mesmo nome. Se o destino existente contiver ícones, não substitua seu `index.theme` nem apague o diretório inteiro. Siga [`tools/hyprbar-cursors/README.md`](tools/hyprbar-cursors/README.md).

## 5. Tema de ícones e fonte Hyprbar

São recursos visuais, não instalações dos aplicativos representados pelos ícones. Na raiz do clone, instale somente se os destinos não existirem:

```sh
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
mkdir -p "$DATA/icons" "$DATA/fonts"
if [ -e "$DATA/icons/hyprbar" ] || [ -L "$DATA/icons/hyprbar" ]; then
    printf '%s\n' 'Destino do tema de ícones já existe; preservado.'
else
    cp -aT --no-clobber tools/hyprbar-icons/hyprbar "$DATA/icons/hyprbar"
fi
if [ -e "$DATA/fonts/Hyprbar" ] || [ -L "$DATA/fonts/Hyprbar" ]; then
    printf '%s\n' 'Destino da fonte já existe; preservado.'
else
    mkdir -p "$DATA/fonts/Hyprbar"
    cp -n assets/fonts/Hyprbar/*.ttf assets/fonts/Hyprbar/OFL.txt "$DATA/fonts/Hyprbar/"
    fc-cache -f "$DATA/fonts/Hyprbar"
fi
fc-match Hyprbar
```

O tema de ícones `hyprbar` e o cursor original de mesmo nome podem compartilhar um diretório instalado: por isso, este comando recusa qualquer destino existente, em vez de substituir seu `index.theme`. Uma mesclagem exige revisão manual. Os ícones herdam Adwaita/hicolor; instale esses fallbacks pela distribuição quando ausentes.

Selecione os ícones na central ou nas configurações do desktop. A fonte é uma derivada renomeada da Adwaita Sans, sob OFL; instalar não a seleciona automaticamente. Para a barra, a opção é `[shell] font_family = "Hyprbar"`, mesclada à configuração existente. Preserve a fonte monoespaçada e as preferências dos demais aplicativos.

Referências: [ícones](tools/hyprbar-icons/README.md), [fonte e licença](assets/fonts/Hyprbar/README.md).

## 6. Extensão Hyprbar · Nova aba (Chrome/Brave)

É uma extensão própria incluída no repositório. Requer Chrome ou Brave já instalado; não instala o navegador. Substitui somente a nova aba normal, com relógio, pesquisa pelo buscador já escolhido e cores do Hyprbar; não modifica sites nem a nova aba anônima.

O bloco abaixo destina-se a uma instalação nova. Recusa colisões antes de copiar. O destino da extensão é fixo em `~/.local/share`, mesmo com `XDG_DATA_HOME` personalizado; o diretório de configuração respeita os overrides:

```sh
(
    set -eu
    CONFIG="${HYPRBAR_CONFIG_HOME:-${XDG_CONFIG_HOME:-$HOME/.config}/hyprbar}"
    EXT="$HOME/.local/share/hyprbar/extensions/newtab"
    for target in "$EXT" "$CONFIG/templates/browser-newtab" "$CONFIG/browser-newtab.toml"; do
        if [ -e "$target" ] || [ -L "$target" ]; then
            printf 'Destino existente; revise antes de instalar: %s\n' "$target" >&2
            exit 1
        fi
    done
    mkdir -p "$EXT" "$CONFIG/templates/browser-newtab"
    cp -n tools/browser-newtab/manifest.json tools/browser-newtab/newtab.html \
        tools/browser-newtab/newtab.css tools/browser-newtab/newtab.js \
        tools/browser-newtab/palette.css "$EXT/"
    cp -n tools/browser-newtab/palette.css.in "$CONFIG/templates/browser-newtab/"
    cp -n tools/browser-newtab/browser-newtab.toml "$CONFIG/"
)
```

Em cada perfil do navegador, abra `chrome://extensions` ou `brave://extensions`, ative **Modo do desenvolvedor**, escolha **Carregar sem compactação** e selecione o caminho absoluto de `~/.local/share/hyprbar/extensions/newtab`. Aceite a substituição da nova aba. Não edite arquivos privados do perfil para ativar a extensão.

Para registrar o template e gerar a paleta, com o Hyprbar ativo:

```sh
hyprbar config reload
hyprbar msg templates-apply
```

Atenção: aplicar templates pode executar hooks já existentes no seu ambiente, inclusive os que reiniciam navegadores. Salve seu trabalho e revise os hooks antes; em uma instalação nova esta extensão não adiciona hooks de reinício. Abas abertas podem precisar de recarga. Detalhes e remoção: [`tools/browser-newtab/README.md`](tools/browser-newtab/README.md).

## 7. Integrações opcionais com aplicativos de terceiros

O repositório fornece os arquivos de integração abaixo, não os aplicativos externos. Não há instalador universal que configure todos eles com segurança; siga as instruções específicas e preserve configurações existentes.

- **Cores do Chrome/Brave:** [`tools/desktop-integration/README.md`](tools/desktop-integration/README.md), seção **Browser colors**. Copie os dois scripts Python para o diretório efetivo `hooks/`, o template para `templates/chrome/manifest.json.in`, mescle o fragmento `browser/chrome-theme.toml` e carregue o tema gerado pela interface de extensões de cada perfil. Brave depende do script Chrome na mesma pasta. Mescle a lista `hooks.colors_changed` sem substituir hooks anteriores. Esse modo **fecha e reinicia navegadores abertos**, pode perder formulários e não garante restauração integral de abas. Só habilite após aceitar esse comportamento. Os padrões são para pacotes nativos Fedora; Flatpak/Snap e caminhos XDG personalizados exigem adaptação dos caminhos de executável, perfis e tema. Não é a mesma extensão de nova aba.
- **Nautilus/Loupe:** no mesmo [README de integrações](tools/desktop-integration/README.md), seção **GTK4**. Copie as pontes CSS selecionadas de `tools/desktop-integration/gtk/` para o diretório efetivo `gtk-4.0/` e mescle os imports depois do import de `hyprbar.css` já gerado. Preserve links simbólicos e faça backup dos alvos. Requer o template GTK4 funcionando e seletores compatíveis com a versão/tema dos aplicativos. Não instala Nautilus/Loupe e não muda as imagens ou o canvas do Loupe.
- **Calculadora no menu:** opcionalmente copie `contrib/plugins/tiaoedi/config-examples/hyprcalculadora.desktop` para `$XDG_DATA_HOME/applications` (padrão `~/.local/share/applications`), somente se o destino estiver livre. Esse lançador abre o painel do plugin, não é outra calculadora independente. Os plugins requerem API 22; confira compatibilidade. Exemplos de widgets e atalhos estão em [`contrib/plugins/tiaoedi/README.md`](contrib/plugins/tiaoedi/README.md). Não copie os TOMLs sobre sua barra inteira: as listas de widgets podem substituir umas às outras.

Templates de Kitty, Alacritty, Qt, GTK e outros programas também não são instaladores desses programas. Configure cada integração separadamente; não copie seus arquivos pessoais inteiros de outra máquina sem revisão.

## 8. O que exige backup separado

O clone preserva o código versionado e o tema `hyprbar-1`, mas não copia automaticamente:

- Configurações pessoais do Hyprland, GTK, atalhos, monitores e inicialização.
- Configuração e estado pessoal do Hyprbar, paletas baixadas, hooks e templates locais.
- Temas baixados em `~/.local/share/icons` (ou `$XDG_DATA_HOME/icons`) e `~/.icons`.
- Perfis, senhas, sessões de navegador, documentos e dados dos aplicativos.
- Scripts pessoais e aplicativos adaptados que não estejam neste repositório.

As adaptações locais **ArtCraft Launcher, PhotoCraft e PdfCraft** não fazem parte deste clone: seus executáveis/fontes e a integração de paleta precisam de backup ou publicação separada. A presença dos comandos no computador antigo não significa que `git clone tiaoedi/hyprbar` os recuperará. O mesmo vale para ferramentas pessoais como `linuxai`, `motocam`/`motoview` e `buscar`/`busca1`; este guia não inventa um instalador para fontes que não estão versionadas aqui.

Não copie configurações completas do computador antigo por cima das novas sem revisar caminhos, monitores e versões. Faça backup antes de formatar e proteja dados privados; não envie credenciais ao GitHub.

## 9. Verificar e diagnosticar

```sh
hyprbar --version
hyprbar msg plugins list
./contrib/apps/hrprbar-install-cursor/run.sh --list
```

O último comando lista cursores em JSON, sem abrir a interface nem aplicar configurações. Abrir a central e seus módulos também não aplica mudanças automaticamente. Instalar um pacote/tema, selecionar uma opção e aplicar uma configuração são etapas diferentes.

Se o lançador informar dependência ausente, resolva a dependência indicada no sistema ou selecione um Python compatível; não use caminhos de ambientes Hermes do outro computador. Não execute testes GUI em lote na sessão de trabalho: eles podem abrir janelas. As verificações do código-fonte são documentadas em `BUILDING.md` e no README do aplicativo.

## 10. Migrar uma configuração Noctalia existente

O Hyprbar usa diretórios XDG próprios e não importa a configuração automaticamente. Confira a ajuda e a prévia antes de aplicar:

```sh
hyprbar config import-noctalia --help
```

A prévia é o comportamento padrão. Use `--apply` somente depois de revisar o que será importado. Consulte também [`docs/user/getting-started/installation.mdx`](docs/user/getting-started/installation.mdx).
