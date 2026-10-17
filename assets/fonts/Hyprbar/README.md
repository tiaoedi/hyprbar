# Hyprbar UI font

Hyprbar is a **renamed derivative of Adwaita Sans 50.0**, itself based on Inter.
The glyph outlines and variable axes are unchanged. It is not a newly drawn
font, Apple's San Francisco, or a copy of Apple's font files. Original credits
and the SIL Open Font License 1.1 are preserved in `OFL.txt` and font metadata.

The two variable files provide upright and italic styles, weight 100–900 and
optical size 14–32. They include the original Portuguese accents and character
coverage. A real Pango/Cairo specimen is supplied as `preview.png`.

To install for the current user, copy this directory's `.ttf` files and `OFL.txt`
to `~/.local/share/fonts/Hyprbar/`, then run:

```sh
fc-cache -f "$HOME/.local/share/fonts/Hyprbar"
fc-match Hyprbar
```

Installation does not require changing system fonts. Optional interface defaults
are `Hyprbar 11` for GTK/GNOME interface text, `Hyprbar 12` for document text and
`[shell] font_family = "Hyprbar"` in an additive Hyprbar config fragment. Preserve
existing monospace fonts, application-specific font choices and configuration
backups. Qt can use the same family through the user Fontconfig sans-serif
preference. Some already-running apps need reopening.

Build and regression-test source: `../../../tools/hyprbar-font/README.md`.
