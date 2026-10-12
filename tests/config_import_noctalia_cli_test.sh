#!/usr/bin/env bash
set -euo pipefail

hyprbar_bin=${1:?usage: config_import_noctalia_cli_test.sh /path/to/hyprbar}
help_output=$("$hyprbar_bin" config import-noctalia --help 2>&1)
[[ "$help_output" == *"Noctalia configuration source directory"* ]]
[[ "$help_output" == *"--apply"* ]]
[[ "$help_output" == *"--config-dir"* ]]
[[ "$help_output" == *"--include-plugin-data"* ]]

scratch_root=${TMPDIR:-"$HOME/.hermes/cache/scratch"}
mkdir -p "$scratch_root"
tmp=$(mktemp -d "$scratch_root/hyprbar-import-test.XXXXXX")
trap 'rm -rf "$tmp"' EXIT

source_config="$tmp/source/config"
source_state="$tmp/source/state"
source_data="$tmp/source/data"
mkdir -p "$source_config/parts" "$source_state" "$source_data/plugins/local-example" \
  "$source_state/plugins/data/author/local-example"
printf '[shell]\nautostart = false\n' > "$source_config/config.toml"
cp "$source_config/config.toml" "$tmp/original-config.toml"
printf '[bar.main]\nposition = "top"\n' > "$source_config/parts/bar.toml"
printf '[theme]\nmode = "dark"\n' > "$source_state/settings.toml"
printf '[ui]\nsetup_completed = true\n' > "$source_state/state.toml"
printf '{"private":"not-imported"}\n' > "$source_state/notification_history.json"
printf '{"mode":"advanced"}\n' > "$source_state/plugins/data/author/local-example/preferences.json"
printf 'id = "local/example"\n' > "$source_data/plugins/local-example/plugin.toml"
printf 'return {}\n' > "$source_data/plugins/local-example/main.lua"

export HYPRBAR_CONFIG_HOME="$tmp/target-config-home"
export HYPRBAR_STATE_HOME="$tmp/target-state-home"
export HYPRBAR_DATA_HOME="$tmp/target-data-home"

preview=$("$hyprbar_bin" config import-noctalia \
  --config-dir "$source_config" --state-dir "$source_state" --data-dir "$source_data")
[[ "$preview" == *"config.toml"* ]]
[[ "$preview" == *"settings.toml"* ]]
[[ ! -e "$HYPRBAR_CONFIG_HOME/hyprbar/config.toml" ]]
[[ ! -e "$HYPRBAR_STATE_HOME/hyprbar/settings.toml" ]]

"$hyprbar_bin" config import-noctalia \
  --config-dir "$source_config" --state-dir "$source_state" --data-dir "$source_data" \
  --apply --include-local-plugins >/dev/null
cmp "$source_config/config.toml" "$HYPRBAR_CONFIG_HOME/hyprbar/config.toml"
cmp "$source_config/parts/bar.toml" "$HYPRBAR_CONFIG_HOME/hyprbar/parts/bar.toml"
cmp "$source_state/settings.toml" "$HYPRBAR_STATE_HOME/hyprbar/settings.toml"
[[ -f "$HYPRBAR_DATA_HOME/hyprbar/plugins/local-example/main.lua" ]]
[[ ! -e "$HYPRBAR_STATE_HOME/hyprbar/state.toml" ]]
[[ ! -e "$HYPRBAR_STATE_HOME/hyprbar/notification_history.json" ]]
[[ ! -e "$HYPRBAR_STATE_HOME/hyprbar/plugins/data/author/local-example/preferences.json" ]]
cmp "$tmp/original-config.toml" "$source_config/config.toml"

no_plugin_config_home="$tmp/no-plugin-config-home"
no_plugin_state_home="$tmp/no-plugin-state-home"
no_plugin_data_home="$tmp/no-plugin-data-home"
HYPRBAR_CONFIG_HOME="$no_plugin_config_home" HYPRBAR_STATE_HOME="$no_plugin_state_home" \
  HYPRBAR_DATA_HOME="$no_plugin_data_home" "$hyprbar_bin" config import-noctalia \
  --config-dir "$source_config" --state-dir "$source_state" --data-dir "$source_data" --apply >/dev/null
[[ -f "$no_plugin_config_home/hyprbar/config.toml" ]]
[[ ! -e "$no_plugin_data_home/hyprbar/plugins/local-example/main.lua" ]]
[[ ! -e "$no_plugin_state_home/hyprbar/plugins/data/author/local-example/preferences.json" ]]
[[ "$(stat -c '%a' "$no_plugin_state_home/hyprbar/settings.toml")" == "600" ]]

plugin_data_config_home="$tmp/plugin-data-config-home"
plugin_data_state_home="$tmp/plugin-data-state-home"
HYPRBAR_CONFIG_HOME="$plugin_data_config_home" HYPRBAR_STATE_HOME="$plugin_data_state_home" \
  HYPRBAR_DATA_HOME="$tmp/plugin-data-data-home" "$hyprbar_bin" config import-noctalia \
  --config-dir "$source_config" --state-dir "$source_state" --data-dir "$source_data" \
  --apply --include-plugin-data >/dev/null
cmp "$source_state/plugins/data/author/local-example/preferences.json" \
  "$plugin_data_state_home/hyprbar/plugins/data/author/local-example/preferences.json"
[[ ! -e "$tmp/plugin-data-data-home/hyprbar/plugins/local-example/main.lua" ]]

collision_config_home="$tmp/collision-config-home"
collision_state_home="$tmp/collision-state-home"
mkdir -p "$collision_config_home/hyprbar"
printf 'keep me\n' > "$collision_config_home/hyprbar/config.toml"
if HYPRBAR_CONFIG_HOME="$collision_config_home" HYPRBAR_STATE_HOME="$collision_state_home" \
  "$hyprbar_bin" config import-noctalia \
  --config-dir "$source_config" --state-dir "$source_state" --data-dir "$source_data" --apply; then
  printf 'import unexpectedly overwrote an existing target\n' >&2
  exit 1
fi
[[ "$(<"$collision_config_home/hyprbar/config.toml")" == "keep me" ]]
[[ ! -e "$collision_state_home/hyprbar/settings.toml" ]]

dangling_target_home="$tmp/dangling-target-home"
mkdir -p "$dangling_target_home/hyprbar"
ln -s "$tmp/nonexistent-target" "$dangling_target_home/hyprbar/config.toml"
if dangling_output=$(HYPRBAR_CONFIG_HOME="$dangling_target_home" HYPRBAR_STATE_HOME="$tmp/dangling-target-state" \
  "$hyprbar_bin" config import-noctalia \
  --config-dir "$source_config" --state-dir "$source_state" --data-dir "$source_data" --apply 2>&1); then
  printf 'import unexpectedly replaced a dangling target symlink\n' >&2
  exit 1
fi
[[ "$dangling_output" == *"target already exists"* ]]
[[ -L "$dangling_target_home/hyprbar/config.toml" ]]
[[ ! -e "$tmp/dangling-target-state/hyprbar/settings.toml" ]]

symlink_config="$tmp/source/symlink-config"
mkdir -p "$symlink_config"
ln -s "$source_config/config.toml" "$symlink_config/linked.toml"
HYPRBAR_CONFIG_HOME="$tmp/symlink-target-config" HYPRBAR_STATE_HOME="$tmp/symlink-target-state" \
  "$hyprbar_bin" config import-noctalia \
  --config-dir "$symlink_config" --state-dir "$source_state" --data-dir "$source_data" --apply >/dev/null
[[ -f "$tmp/symlink-target-config/hyprbar/linked.toml" ]]
[[ ! -L "$tmp/symlink-target-config/hyprbar/linked.toml" ]]
cmp "$source_config/config.toml" "$tmp/symlink-target-config/hyprbar/linked.toml"

broken_symlink_config="$tmp/source/broken-symlink-config"
mkdir -p "$broken_symlink_config"
ln -s "$tmp/nonexistent-source" "$broken_symlink_config/broken.toml"
if HYPRBAR_CONFIG_HOME="$tmp/broken-target-config" HYPRBAR_STATE_HOME="$tmp/broken-target-state" \
  "$hyprbar_bin" config import-noctalia \
  --config-dir "$broken_symlink_config" --state-dir "$source_state" --data-dir "$source_data" --apply; then
  printf 'import unexpectedly accepted a broken config symlink\n' >&2
  exit 1
fi
[[ ! -e "$tmp/broken-target-config/hyprbar/broken.toml" ]]
[[ ! -e "$tmp/broken-target-state/hyprbar/settings.toml" ]]

