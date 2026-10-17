# hyprbar — tema de ícones original

Tema vetorial com **62 ícones canônicos originais** e **104 aliases por links
simbólicos internos**: 166 entradas SVG no total. Nome da pasta e `Name` são
exatamente `hyprbar`. Licença MIT para código e ilustrações.

## Direção visual

Tiles quadrados de cantos arredondados, gradientes verticais, brilho discreto e
sombras contidas; pastas azuis com aba e documentos com dobra. A inspiração é a
linguagem visual de desktops modernos, não a reprodução de ativos do macOS.
Não há logotipo da Apple, rosto do Finder, emblema do Safari ou logotipos oficiais
de aplicativos. Chrome usa janela/globo; Brave, escudo; Firefox, raposa geométrica;
OBS, enquadramento/captura; VLC, reprodução. Os identificadores de aplicativos são
somente compatibilidade de lookup e não indicam afiliação às respectivas marcas.

Os SVGs têm geometria própria, são autossuficientes e não usam scripts, imagens
externas, fontes, `<text>`, referências remotas ou artwork incorporado de terceiros.
As legendas dos PNGs de inspeção usam fonte local, fora dos SVGs.

## Cobertura

- Pastas: genérica, home, documentos, downloads, música, imagens, vídeos,
  desktop, modelos, compartilhamento público, configuração, código e remota.
- Lixeira vazia/cheia; discos, USB, rede, computador, telefone, impressora e fones.
- MIME: texto, PDF, imagem, áudio, vídeo, arquivo compactado, código, planilha,
  apresentação, documento de escritório e executável.
- Aplicativos: Nautilus, Hyprbar, Chrome/Chromium, Brave, Firefox, Kitty/terminal,
  VS Code, VLC, OBS, GIMP, LibreOffice Writer/Calc/Impress/Draw/startcenter,
  Telegram, Discord, Bitwarden (incluindo o identificador do atalho Brave
  solicitado), Pavucontrol, calculadora, calendário, configurações, software,
  editor de texto, captura de tela, relógio, ajuda e busca.

`manifest.json` é o inventário completo, com nomes case-sensitive, caminhos,
contextos, glyphs, paletas, destinos de aliases e totais calculados pelo gerador.
Aliases não são contabilizados como ilustrações originais.

## Estrutura

```text
generate.py            # geometria e catálogo originais; geração determinística
verify.py              # renderização e lookup GTK isolado, sem mudar preferências
test_theme.py          # testes de contrato, unicidade, segurança e execução
manifest.json          # inventário exato gerado
verification.json      # resultado da última verificação real
LICENSE
previews/contact-sheet.png
previews/size-check.png # comparativo 16/32/64/128 px sem reescalar
hyprbar/               # diretório do tema pronto para instalação posterior
  index.theme
  LICENSE
  scalable/{apps,devices,mimetypes,places}/
```

## Regenerar e testar — não instala nem aplica

Na pasta deste projeto:

```sh
/usr/bin/python3 generate.py
/usr/bin/python3 -m unittest -v
# opcional: imprimir relatório detalhado e refazer previews
/usr/bin/python3 verify.py
```

Requisitos locais já utilizados: Python 3 do sistema, PyGObject, GTK 4, Rsvg 2 e
Pycairo. Nenhum download ou pacote adicional é necessário neste ambiente. O
verificador não depende de abrir janela nem obter o Gtk.Settings do desktop.
Cria um `Gtk.IconTheme` isolado e define explicitamente somente sua busca.
PNGs individuais ficam em subpastas do diretório temporário do Python
(respeitando `TMPDIR`); o caminho real está no relatório local.

A suíte verifica XML e viewBox, ausência de elementos SVG ativos/externos,
colisão de nomes, unicidade dos SVGs canônicos, correspondência do manifest,
links simbólicos resolvidos dentro do tema e presença dos nomes solicitados.
Renderiza todos os 62 SVGs em 16, 32, 64 e 128 px (**248 renders**), verifica
opacidade visível e margens transparentes; faz **664 lookups GTK** (166 entradas
em quatro tamanhos) e confirma o arquivo exato de origem em vez de aceitar
fallback silencioso. A folha de tamanhos inclui amostras claras e a folha geral
mostra todos os canônicos sobre fundo escuro. A qualidade visual exige também
inspeção das previews: o teste automatizado não prova originalidade artística.

## Fallback e Nautilus

`Inherits=Adwaita,hicolor`. Não há diretório `actions` nem qualquer override
`*-symbolic`. Assim, o Nautilus pode usar `folder-symbolic` herdado na barra
lateral, mantendo contraste e adaptação ao tema; a pasta colorida regular aparece
onde o aplicativo solicita o ícone regular, como a grade de arquivos. Nem toda
superfície de todo aplicativo adota o tema: ícones internos/embutidos podem
continuar próprios. O verificador confirma quatro lookups simbólicos provenientes
do Adwaita (pasta, lixeira, navegação e rede), sem copiar assets de fallback.

## Instalação posterior, fora do escopo deste build

O artefato instalável é somente o diretório `hyprbar/`, incluindo `index.theme`,
`LICENSE` e `scalable/`. Quem instalar posteriormente deve preservar os links
simbólicos, o nome exato e a estrutura. A árvore já pode ser examinada sem instalar.
Este build **não** copiou o tema para diretórios do usuário/sistema, mudou o tema
ativo, criou caches de ícones instalados, reiniciou aplicativos ou fez operações
de stage/commit/push. Demais arquivos do repositório não foram alterados.
