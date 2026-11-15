# Hyprbar Cursor Theme

An original cursor theme named `hyprbar`, with a clean, rounded macOS-inspired feel. It uses a white body, charcoal outline, and restrained blue details. It contains no Apple logos, emblems, or copied Apple artwork.

The generator creates both standard Xcursor images (for GTK and legacy consumers) and a Hyprcursor theme (`manifest.hl` plus one ZIP archive per shape) for the Hyprland compositor. It uses ImageMagick's installed SVG renderer and Python's standard library; it does not install packages.

## Build and verify

From this directory:

```sh
python3 generate.py
python3 verify.py
python3 test_sizes.py
```

Generation requires Python 3 and ImageMagick (`magick`). Verification also requires Pillow and `libXcursor.so.1`.

Verification checks the Xcursor binary structure and hotspots, loads every canonical cursor with `libXcursor`, checks that all aliases resolve inside the theme, and writes `previews/contact-sheet.png`. The regression test checks that every cursor and alias loads at the requested 24, 32, or 48 pixel size, rather than falling back to a 48 pixel image in XWayland applications such as Brave.

## hyprbar-1 variant

The `hyprbar-1/` directory contains the separately packaged blue-black/red variant: body `#101a2b`, inset `#263b57`, outline `#8298b5`, and accents `#ce454f`. It preserves the original theme and includes its MIT license, editable SVGs in `sources/`, and a light/dark contact sheet in `preview.png`.

It provides 22 static shapes, 39 relative aliases, Xcursor sizes 24, 28, 32, 40, 48 and 64 px, and scalable Hyprcursor SVG archives. These are prebuilt assets; `generate.py` and the existing regression scripts target only the original `hyprbar` theme, not this variant.

From this directory, install the variant only if the destination does not already exist:

```sh
mkdir -p "$HOME/.local/share/icons"
cp -aT --no-clobber hyprbar-1 "$HOME/.local/share/icons/hyprbar-1"
```

Do not merge with a different existing installation. Select `hyprbar-1` separately in your cursor settings (28 px is available); copying does not activate it or alter desktop configuration. The cursor manager under `../../contrib/apps/hrprbar-install-cursor/` can discover the installed theme. No personal desktop settings or machine-local aliases are included.

## Install manually

Copy or merge the generated `hyprbar/` directory into `~/.local/share/icons/hyprbar/` (this can coexist with the existing Hyprbar icon theme), then choose `hyprbar` in your desktop's cursor theme setting. This repository change does not install or activate it automatically.

Preserve any existing `index.theme` and icon assets when merging: copy only `cursors/`, `hyprcursors/`, and `manifest.hl` into an existing Hyprbar icon theme. Applications that cache cursor images may need to be restarted after a theme update.
