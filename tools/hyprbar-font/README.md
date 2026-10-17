# Rebuild the Hyprbar font derivative

`build_font.py` renames the installed, OFL-licensed Adwaita Sans files while
preserving glyphs, cmap, original credits, license and variable axes. It does not
copy Apple's font files or modify system fonts. The prebuilt derivative and
license are in `../../assets/fonts/Hyprbar/`.

The current input paths match Fedora's `adwaita-sans-fonts` package:

- `/usr/share/fonts/adwaita-sans-fonts/AdwaitaSans-Regular.ttf`
- `/usr/share/fonts/adwaita-sans-fonts/AdwaitaSans-Italic.ttf`
- `/usr/share/licenses/adwaita-sans-fonts/LICENSE`

The tested source version was 50.0. On a different distribution, review/adapt the
source constants and re-check licensing before running; do not silently replace
them with unrelated fonts. FontTools 4.67.0 was used in an isolated uv environment
without a global Python package installation.

From this directory:

```sh
uv run --no-project --with fonttools==4.67.0 python test_font.py -v
uv run --no-project --with fonttools==4.67.0 python build_font.py --output /path/to/output
```

Tests use Python's temporary directory (respecting `TMPDIR`) and verify the saved
font tables/checksums, naming, cmap/glyph inventory, variable axes, Portuguese
characters and exact license text. Generated TTF files are modified font software
and remain under OFL 1.1; the project's other licenses do not replace the bundled
font license. Read `../../assets/fonts/Hyprbar/OFL.txt` before redistribution.
