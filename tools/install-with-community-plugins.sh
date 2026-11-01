#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
plugin_source="$repo_root/contrib/plugins/tiaoedi"
data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
plugin_root="$data_home/hyprbar/plugins"

for command in git just meson; do
  command -v "$command" >/dev/null 2>&1 || {
    printf 'Erro: comando obrigatório não encontrado: %s\n' "$command" >&2
    exit 1
  }
done

for plugin in calculator wellbeing; do
  [[ -f "$plugin_source/$plugin/plugin.toml" ]] || {
    printf 'Erro: manifesto ausente: %s\n' "$plugin_source/$plugin/plugin.toml" >&2
    exit 1
  }
  [[ ! -e "$plugin_root/$plugin" ]] || {
    printf 'Erro: destino já existe; preservado sem alterações: %s\n' "$plugin_root/$plugin" >&2
    exit 1
  }
done

printf 'Compilando Hyprbar em modo release...\n'
cd "$repo_root"
just configure release
just build release
sudo just install release

mkdir -p "$plugin_root"
for plugin in calculator wellbeing; do
  cp -a "$plugin_source/$plugin" "$plugin_root/$plugin"
done

printf '\nHyprbar e os plugins calculator e wellbeing foram instalados.\n'
printf 'Para ativar os plugins, execute em uma sessão Hyprbar ativa:\n'
printf '  hyprbar msg plugins enable tiaoedi/calculator\n'
printf '  hyprbar msg plugins enable tiaoedi/wellbeing\n'
printf 'Os atalhos opcionais Super+F7 e Super+F9 e as configurações de exemplo\n'
printf 'não são aplicados automaticamente para preservar sua configuração.\n'
printf 'Plugins das fontes externas oficial/community também são gerenciados à parte em Configurações → Plugins.\n'
