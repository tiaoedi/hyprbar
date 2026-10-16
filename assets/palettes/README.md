# hyprbar moderno

Paleta personalizada para o Hyprbar, com variantes escura e clara.

- Escura: grafite azulado, texto branco frio, azul suave como destaque,
  verde-água como cor secundária e champanhe como detalhe terciário.
- Clara: branco frio, texto grafite e os mesmos destaques em tons mais profundos.
- Inclui as 16 cores ANSI e cores de cursor e seleção para templates de terminal.
- Todos os pares de texto/interface definidos na paleta têm contraste mínimo
  de 4,5:1, incluindo texto secundário, hover e seleção do terminal.

## Instalação

Na raiz do repositório, copie a paleta para o diretório de configuração:

```sh
config_home="${HYPRBAR_CONFIG_HOME:-${XDG_CONFIG_HOME:-$HOME/.config}}"
mkdir -p "$config_home/hyprbar/palettes"
cp -n 'assets/palettes/hyprbar moderno.json' "$config_home/hyprbar/palettes/"
```

Em Configurações → Aparência → Tema, selecione a fonte Personalizada e
escolha `hyprbar moderno`. A paleta também fica disponível no seletor de
paletas personalizadas do painel de papel de parede.

Para ativar pela linha de comando (altera o tema ativo):

```sh
hyprbar msg color-scheme-set custom 'hyprbar moderno'
```

O modo claro/escuro é controlado pelas configurações normais do Hyprbar.
A paleta não altera layout, fontes, papel de parede nem o catálogo existente.
Os templates e hooks já configurados podem ser executados ao ativar o tema,
conforme o comportamento normal do Hyprbar.

## Validação sem ativar

```sh
hyprbar theme --theme-json 'assets/palettes/hyprbar moderno.json' --both
```

Usa o parser real do Hyprbar e expande ambas as variantes para os tokens
consumidos pelo sistema de temas e templates.
