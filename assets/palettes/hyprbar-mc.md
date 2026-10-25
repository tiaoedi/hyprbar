# hyprbar-mc

Paleta e preset de aparência para o Hyprbar nativo. O conjunto visual fica em `assets/themes/hyprbar-mc/`; o JSON deste diretório contém apenas as cores. Não é um produto oficial Apple nem implementa o compositor Liquid Glass.

## Aparência atual

- Fundo escuro: `#1E1E20`, igual ao fundo do Kitty em uso.
- Texto escuro: `#F5F5F7`, igual ao foreground do terminal.
- Superfícies principais e variantes usam o mesmo fundo, sem diferença entre barra, painéis, cartões e menus padrão.
- Variante clara: fundo `#F5F5F7` e texto `#1D1D1F`, também compartilhados com o terminal dessa variante.
- Hover/seleção usam as cores de seleção do terminal; acentos e alertas continuam distinguíveis.
- As cores de destaque têm sua origem documentada em `assets/themes/hyprbar-mc/apple-colors.json`. Superfícies neutras são adaptações, não uma exportação de NSColor do macOS.

O preset completo usa superfícies sólidas para evitar que transparência e papel de parede alterem as cores. Mantém a identidade Hyprbar no botão do menu. Os botões padrão de janela foram desativados nas configurações GTK do usuário; aplicativos com controles próprios podem ignorá-las.

## Instalação somente da paleta

```sh
config_home="${HYPRBAR_CONFIG_HOME:-${XDG_CONFIG_HOME:-$HOME/.config}}"
mkdir -p "$config_home/hyprbar/palettes"
cp -n assets/palettes/hyprbar-mc.json "$config_home/hyprbar/palettes/"
```

Selecionar `Personalizada → hyprbar-mc` muda somente a paleta. O layout completo depende do preset TOML e do módulo Lua fornecidos separadamente; overrides em `settings.toml` têm prioridade e precisam ser preservados conscientemente.

A ativação pode executar os templates e hooks já configurados, inclusive hooks de navegador.

## Validação

```sh
hyprbar theme --theme-json assets/palettes/hyprbar-mc.json --both
hyprbar config validate assets/themes/hyprbar-mc/preset.toml
```

Verificados no parser instalado: `surface`, `surface_variant`, `surface_container` e `background` correspondem ao `terminal.background` em ambos os modos; os foregrounds correspondem a `terminal.foreground`. A barra ativa e uma área vazia do Kitty foram amostradas na tela e retornaram RGB `(30,30,32)` em ambas. Central de Controle e lançador também foram inspecionados visualmente.

Imagens, ícones de aplicativos, seleções, controles ativos e alertas não são todos pintados com uma única cor: preservam informação e estados funcionais. A igualdade de fundo não implica controle sobre conteúdo arbitrário de outros aplicativos.
