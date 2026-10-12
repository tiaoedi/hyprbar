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
printf '[shell]\nautostart = false\n' > "$symlink_config/linked-original.toml"
ln -s "linked-original.toml" "$symlink_config/linked.toml"
HYPRBAR_CONFIG_HOME="$tmp/symlink-target-config" HYPRBAR_STATE_HOME="$tmp/symlink-target-state" \
  "$hyprbar_bin" config import-noctalia \
  --config-dir "$symlink_config" --state-dir "$source_state" --data-dir "$source_data" --apply >/dev/null
[[ -f "$tmp/symlink-target-config/hyprbar/linked.toml" ]]
[[ ! -L "$tmp/symlink-target-config/hyprbar/linked.toml" ]]
cmp "$symlink_config/linked-original.toml" "$tmp/symlink-target-config/hyprbar/linked.toml"

external_symlink_config="$tmp/source/external-symlink-config"
external_secret="$tmp/source/outside-config-secret.toml"
mkdir -p "$external_symlink_config"
printf '[private]\nvalue = "must-not-be-imported"\n' > "$external_secret"
ln -s "$external_secret" "$external_symlink_config/linked.toml"
external_target_home="$tmp/external-symlink-target-home"
if HYPRBAR_CONFIG_HOME="$external_target_home" HYPRBAR_STATE_HOME="$tmp/external-symlink-target-state" \
  "$hyprbar_bin" config import-noctalia \
  --config-dir "$external_symlink_config" --state-dir "$source_state" --data-dir "$source_data" --apply; then
  printf 'import unexpectedly followed a config symlink outside its source tree\n' >&2
  exit 1
fi
[[ ! -e "$external_target_home/hyprbar/linked.toml" ]]
[[ -f "$external_secret" ]]

external_settings_state="$tmp/source/external-settings-state"
external_settings_secret="$tmp/source/outside-settings-secret.toml"
mkdir -p "$external_settings_state"
printf '[private]\nvalue = "must-not-be-imported"\n' > "$external_settings_secret"
ln -s "$external_settings_secret" "$external_settings_state/settings.toml"
external_settings_target="$tmp/external-settings-target-home"
if HYPRBAR_CONFIG_HOME="$external_settings_target" HYPRBAR_STATE_HOME="$tmp/external-settings-target-state" \
  "$hyprbar_bin" config import-noctalia \
  --config-dir "$source_config" --state-dir "$external_settings_state" --data-dir "$source_data" --apply; then
  printf 'import unexpectedly followed a settings symlink outside its source tree\n' >&2
  exit 1
fi
[[ ! -e "$external_settings_target/hyprbar/config.toml" ]]
[[ ! -e "$tmp/external-settings-target-state/hyprbar/settings.toml" ]]
[[ -f "$external_settings_secret" ]]

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

# Target config root overlaps source state root. Check both source and target remain untouched.
cross_root="$tmp/cross-root"
mkdir -p "$cross_root/source-config" "$cross_root/target/hyprbar" "$cross_root/data"
printf 'preserve source\n' > "$cross_root/source-config/config.toml"
printf 'state marker\n' > "$cross_root/target/hyprbar/settings.toml"
if HYPRBAR_CONFIG_HOME="$cross_root/target" HYPRBAR_STATE_HOME="$tmp/cross-target-state" \
  "$hyprbar_bin" config import-noctalia --config-dir "$cross_root/source-config" \
  --state-dir "$cross_root/target/hyprbar" --data-dir "$cross_root/data" --apply >/dev/null 2>&1; then
  printf 'import unexpectedly allowed a cross-category source/target overlap\n' >&2
  exit 1
fi
[[ "$(<"$cross_root/source-config/config.toml")" == "preserve source" ]]
[[ "$(<"$cross_root/target/hyprbar/settings.toml")" == "state marker" ]]
[[ ! -e "$cross_root/target/hyprbar/config.toml" ]]

# With local plugins enabled, a target data root must not overlap another source root.
data_overlap="$tmp/data-overlap"
mkdir -p "$data_overlap/source-config" "$data_overlap/source-state" \
  "$data_overlap/source-data/plugins/local-example"
printf 'config marker\n' > "$data_overlap/source-config/config.toml"
printf 'id = "local/example"\n' > "$data_overlap/source-data/plugins/local-example/plugin.toml"
printf 'return {}\n' > "$data_overlap/source-data/plugins/local-example/main.lua"
if HYPRBAR_CONFIG_HOME="$data_overlap/safe-config-home" HYPRBAR_STATE_HOME="$data_overlap/safe-state-home" \
  HYPRBAR_DATA_HOME="$data_overlap/source-config" "$hyprbar_bin" config import-noctalia \
  --config-dir "$data_overlap/source-config" --state-dir "$data_overlap/source-state" \
  --data-dir "$data_overlap/source-data" --include-local-plugins --apply >/dev/null 2>&1; then
  printf 'import unexpectedly allowed a local-plugin target to overlap another source root\n' >&2
  exit 1
fi
[[ "$(<"$data_overlap/source-config/config.toml")" == "config marker" ]]
[[ ! -e "$data_overlap/source-config/hyprbar/plugins/local-example/main.lua" ]]

# A target path whose existing ancestor redirects into a source must also be rejected.
symlink_source="$tmp/symlink-source"
mkdir -p "$symlink_source/config" "$symlink_source/state" "$symlink_source/data"
printf 'preserve through ancestor symlink\n' > "$symlink_source/config/config.toml"
ln -s "$symlink_source/config" "$tmp/symlink-target-link"
if HYPRBAR_CONFIG_HOME="$tmp/symlink-target-link" HYPRBAR_STATE_HOME="$tmp/safe-target-state" \
  "$hyprbar_bin" config import-noctalia --config-dir "$symlink_source/config" \
  --state-dir "$symlink_source/state" --data-dir "$symlink_source/data" --apply >/dev/null 2>&1; then
  printf 'import unexpectedly allowed target ancestry through a symlink\n' >&2
  exit 1
fi
[[ "$(<"$symlink_source/config/config.toml")" == "preserve through ancestor symlink" ]]
[[ ! -e "$symlink_source/config/hyprbar/config.toml" ]]

# A source root reached through a symlinked parent must still overlap a target inside its real path.
source_alias_root="$tmp/source-parent-alias"
source_real_root="$source_alias_root/real"
source_link_root="$source_alias_root/link"
mkdir -p "$source_real_root/config" "$source_real_root/state" "$source_real_root/data"
printf 'preserve source through parent symlink\n' > "$source_real_root/config/config.toml"
ln -s "$source_real_root" "$source_link_root"
if HYPRBAR_CONFIG_HOME="$source_real_root/config/target-home" \
  HYPRBAR_STATE_HOME="$tmp/source-parent-target-state" \
  "$hyprbar_bin" config import-noctalia --config-dir "$source_link_root/config" \
  --state-dir "$source_real_root/state" --data-dir "$source_real_root/data" --apply >/dev/null 2>&1; then
  printf 'import unexpectedly allowed a source root through a symlinked parent to overlap its target\n' >&2
  exit 1
fi
[[ "$(<"$source_real_root/config/config.toml")" == "preserve source through parent symlink" ]]
[[ ! -e "$source_real_root/config/target-home" ]]

# Data roots are inactive without --include-local-plugins and must not trigger writes or block config/state import.
inactive_data_config_home="$tmp/inactive-data-config-home"
inactive_data_state_home="$tmp/inactive-data-state-home"
HYPRBAR_CONFIG_HOME="$inactive_data_config_home" HYPRBAR_STATE_HOME="$inactive_data_state_home" \
  HYPRBAR_DATA_HOME="$source_config" "$hyprbar_bin" config import-noctalia \
  --config-dir "$source_config" --state-dir "$source_state" --data-dir "$source_data" --apply >/dev/null
[[ -f "$inactive_data_config_home/hyprbar/config.toml" ]]
[[ -f "$inactive_data_state_home/hyprbar/settings.toml" ]]
[[ ! -e "$source_config/hyprbar" ]]

# A mid-import copy failure must remove both copied files and newly created directories.
rollback_source="$tmp/rollback-source"
rollback_target_home="$tmp/rollback-target-home"
mkdir -p "$rollback_source/config" "$rollback_source/state" "$rollback_source/data"
printf 'copy this file first\n' > "$rollback_source/config/a-readable.toml"
printf 'this file must be unreadable\n' > "$rollback_source/config/z-unreadable.toml"
chmod 000 "$rollback_source/config/z-unreadable.toml"
if [[ -r "$rollback_source/config/z-unreadable.toml" ]]; then
  printf 'config import directory-rollback case skipped: unreadable fixture is readable by this user\n'
else
  if rollback_output=$(HYPRBAR_CONFIG_HOME="$rollback_target_home/config" \
    HYPRBAR_STATE_HOME="$rollback_target_home/state" HYPRBAR_DATA_HOME="$rollback_target_home/data" \
    "$hyprbar_bin" config import-noctalia --config-dir "$rollback_source/config" \
    --state-dir "$rollback_source/state" --data-dir "$rollback_source/data" --apply 2>&1); then
    printf 'import unexpectedly succeeded with an unreadable source file\n' >&2
    exit 1
  fi
  [[ "$rollback_output" == *"copied files were rolled back"* ]]
  [[ ! -e "$rollback_target_home/config/hyprbar/a-readable.toml" ]]
  if [[ -e "$rollback_target_home/config/hyprbar" ]]; then
    printf 'rollback left a newly created destination directory behind\n' >&2
    exit 1
  fi
fi

# Existing target ancestors that resolve into a source root must be rejected before copying.
nested_source="$tmp/nested-target-source"
nested_target_home="$tmp/nested-target-home"
mkdir -p "$nested_source/config/parts" "$nested_source/config/other" "$nested_source/state" \
  "$nested_source/data" "$nested_target_home/config/hyprbar"
printf '[shell]\nautostart = false\n' > "$nested_source/config/config.toml"
printf '[part]\nvalue = 1\n' > "$nested_source/config/parts/new.toml"
ln -s "$nested_source/config/other" "$nested_target_home/config/hyprbar/parts"
if nested_output=$(HYPRBAR_CONFIG_HOME="$nested_target_home/config" \
  HYPRBAR_STATE_HOME="$nested_target_home/state" HYPRBAR_DATA_HOME="$nested_target_home/data" \
  "$hyprbar_bin" config import-noctalia --config-dir "$nested_source/config" \
  --state-dir "$nested_source/state" --data-dir "$nested_source/data" --apply 2>&1); then
  printf 'import unexpectedly succeeded through a target-parent symlink into the source tree\n' >&2
  exit 1
fi
[[ "$nested_output" == *"overlap"* ]]
[[ ! -e "$nested_target_home/config/hyprbar/config.toml" ]]
[[ ! -e "$nested_source/config/other/new.toml" ]]
