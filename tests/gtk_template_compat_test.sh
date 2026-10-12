#!/usr/bin/env bash
set -euo pipefail

templates_dir=$1
apply_script="$templates_dir/gtk/apply.sh"
work_dir=$(mktemp -d)
trap 'rm -rf "$work_dir"' EXIT

home="$work_dir/home"
stub_dir="$work_dir/bin"
mkdir -p "$home" "$stub_dir"
cat >"$stub_dir/gsettings" <<'STUB'
#!/usr/bin/env sh
if [ "${1:-}" = "list-schemas" ]; then
  printf '%s\n' org.gnome.desktop.interface
fi
exit 0
STUB
chmod +x "$stub_dir/gsettings"
export HOME="$home"
export PATH="$stub_dir:$PATH"

fail() {
  printf '%s\n' "gtk_template_compat_test: FAIL: $*" >&2
  exit 1
}

count_exact_line() {
  local file=$1 line=$2
  grep -Fxc -- "$line" "$file" || true
}

prepare_case() {
  local name=$1
  local config_home="$work_dir/$name/config"
  mkdir -p "$config_home/gtk-3.0" "$config_home/gtk-4.0"
  printf '/* generated GTK3 theme */\n' >"$config_home/gtk-3.0/hyprbar.css"
  printf '/* generated GTK4 theme */\n' >"$config_home/gtk-4.0/hyprbar.css"
  printf '%s\n' "$config_home"
}

run_apply() {
  local config_home=$1 output
  if ! output=$(XDG_CONFIG_HOME="$config_home" XDG_DATA_HOME="$home/data" bash "$apply_script" dark 2>&1); then
    fail "apply.sh failed for $config_home: ${output:-no diagnostic output}"
  fi
}

assert_migrated() {
  local config_home=$1 gtk_version=$2
  local gtk_css="$config_home/gtk-$gtk_version.0/gtk.css"
  local new_import='@import url("hyprbar.css");'
  local old_import='@import url("noctalia.css");'
  [ "$(count_exact_line "$gtk_css" "$new_import")" -eq 1 ] || fail "expected exactly one Hyprbar import in GTK$gtk_version"
  [ "$(count_exact_line "$gtk_css" "$old_import")" -eq 0 ] || fail "legacy Noctalia import remains in GTK$gtk_version"
  grep -Fq 'body { color: red; }' "$gtk_css" || fail "unrelated GTK$gtk_version CSS was lost"
}

for version in 3 4; do
  config_home=$(prepare_case "legacy-$version")
  printf '@import url("noctalia.css");\nbody { color: red; }\n' >"$config_home/gtk-$version.0/gtk.css"
  printf 'legacy theme\n' >"$config_home/gtk-$version.0/noctalia.css"
  run_apply "$config_home"
  assert_migrated "$config_home" "$version"
  cp "$config_home/gtk-$version.0/gtk.css" "$work_dir/legacy-$version.before"
  run_apply "$config_home"
  cmp -s "$work_dir/legacy-$version.before" "$config_home/gtk-$version.0/gtk.css" \
    || fail "repeated apply changed GTK$version imports"
  XDG_CONFIG_HOME="$config_home" bash "$templates_dir/gtk/undo-gtk$version.sh" >/dev/null 2>&1 \
    || fail "undo failed for GTK$version"
  [ "$(count_exact_line "$config_home/gtk-$version.0/gtk.css" '@import url("hyprbar.css");')" -eq 0 ] \
    || fail "undo left the Hyprbar import in GTK$version"
  grep -Fq 'body { color: red; }' "$config_home/gtk-$version.0/gtk.css" \
    || fail "undo removed unrelated GTK$version CSS"
  [ ! -e "$config_home/gtk-$version.0/hyprbar.css" ] || fail "undo left the GTK$version theme file"

done

for version in 3 4; do
  config_home=$(prepare_case "writable-symlink-$version")
  gtk_dir="$config_home/gtk-$version.0"
  target="$gtk_dir/gtk-source.css"
  printf '@import url("noctalia.css");\nbody { color: red; }\n' >"$target"
  ln -s gtk-source.css "$gtk_dir/gtk.css"
  run_apply "$config_home"
  [ -L "$gtk_dir/gtk.css" ] || fail "writable GTK$version symlink was replaced"
  assert_migrated "$config_home" "$version"

  config_home=$(prepare_case "readonly-symlink-$version")
  gtk_dir="$config_home/gtk-$version.0"
  target="$gtk_dir/gtk-source.css"
  printf '@import url("noctalia.css");\nbody { color: red; }\n' >"$target"
  chmod 444 "$target"
  ln -s gtk-source.css "$gtk_dir/gtk.css"
  if [ ! -w "$target" ]; then
    run_apply "$config_home"
    [ ! -L "$gtk_dir/gtk.css" ] || fail "read-only GTK$version symlink was not localized"
    assert_migrated "$config_home" "$version"
    grep -Fq '@import url("noctalia.css");' "$target" || fail "read-only GTK$version symlink target was modified"
  fi

done

config_home=$(prepare_case both-imports)
cat >"$config_home/gtk-3.0/gtk.css" <<'CSS'
@import url("noctalia.css");
@import url("hyprbar.css");
@import url("hyprbar.css");
body { color: red; }
CSS
cat >"$config_home/gtk-4.0/gtk.css" <<'CSS'
@import url("noctalia.css");
@import url("hyprbar.css");
@import url("hyprbar.css");
body { color: red; }
CSS
run_apply "$config_home"
assert_migrated "$config_home" 3
assert_migrated "$config_home" 4

config_home=$(prepare_case no-import)
printf 'body { color: red; }\n' >"$config_home/gtk-3.0/gtk.css"
printf 'body { color: red; }\n' >"$config_home/gtk-4.0/gtk.css"
run_apply "$config_home"
assert_migrated "$config_home" 3
assert_migrated "$config_home" 4

# If the final write fails, an existing gtk.css must remain unchanged rather than truncated.
config_home=$(prepare_case write-failure)
gtk_css="$config_home/gtk-3.0/gtk.css"
printf '@import url("noctalia.css");\n' >"$gtk_css"
for _ in {1..80}; do
  printf 'body { color: red; }\n' >>"$gtk_css"
done
cp "$gtk_css" "$work_dir/write-failure.before"
failure_bin="$work_dir/failure-bin"
mkdir -p "$failure_bin"
cat >"$failure_bin/cat" <<'STUB'
#!/usr/bin/env sh
ulimit -f 1
exec /usr/bin/cat "$@"
STUB
chmod +x "$failure_bin/cat"
if PATH="$failure_bin:$PATH" XDG_CONFIG_HOME="$config_home" XDG_DATA_HOME="$home/data" \
  bash "$apply_script" dark >/dev/null 2>&1; then
  assert_migrated "$config_home" 3
else
  cmp -s "$work_dir/write-failure.before" "$gtk_css" \
    || fail "failed GTK stylesheet update left the original file truncated or partial"
fi

printf '%s\n' 'gtk_template_compat_test: PASS'
