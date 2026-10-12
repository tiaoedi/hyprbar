# Credits

Hyprbar is an independent fork based on the Noctalia v5.2.1 source project, commit
[`6ef43e2bf2f3d5b4205ec72a72e34a2ab76ce3b4`](https://github.com/noctalia-dev/noctalia/commit/6ef43e2bf2f3d5b4205ec72a72e34a2ab76ce3b4).
Upstream source and contributor credits are preserved below; see `LICENSE` for the upstream license.

## Hyprbar design & branding

- **Hyprbar icon and wallpaper** — Original vector artwork created for this fork.
- **[Tabler Icons](https://tabler.io/icons)** — Icon set used throughout the shell (MIT; bundled-font license text is in `assets/fonts/tabler-icons-license.txt`)
- **Documentation screenshots** — Images retained from the original shell documentation. Screenshots marked `*-v5.png` show an earlier interface, not a current Hyprbar build.

## Source design and artwork attribution

These are source-attribution acknowledgments: the original project logo and Talia artwork are not bundled as standalone assets, though retained documentation screenshots may show the earlier interface. These credits do not claim endorsement or additional permission.

- **MrDowntempo** — Creator of the original owl and moon logo
- **[SaberJ2X](https://www.reddit.com/user/SaberJ64/)** — Creator of Talia, the original project mascot
- **[Riyan Resdian on Noun Project](https://thenounproject.com/creator/yaicon/)** — Plug-icon acknowledgment retained from the source credits; this fork does not include a separate Noun Project plug asset.

## System Libraries

Provided by system packages at build time and linked dynamically where applicable:

- **[Wayland](https://wayland.freedesktop.org/)** (`wayland-client`, `wayland-protocols`, `wayland-egl`) — Display protocol
- **[Mesa / EGL / GLES2](https://www.mesa3d.org/)** (or **[libepoxy](https://github.com/anholt/libepoxy)** as fallback) — OpenGL ES context and dispatch
- **[Cairo](https://www.cairographics.org/)** — 2D graphics surface used for text and SVG rasterization
- **[Pango](https://pango.gnome.org/)** / **PangoCairo** — Text layout and shaping
- **[HarfBuzz](https://harfbuzz.github.io/)** — OpenType font metrics used for stable text alignment
- **[FreeType](https://freetype.org/)** — Font rasterization
- **[Fontconfig](https://www.fontconfig.org/)** — Font discovery
- **[librsvg](https://wiki.gnome.org/Projects/LibRsvg)** — SVG rendering (filters, clipPaths, masks)
- **[GLib / GObject / GIO](https://gitlab.gnome.org/GNOME/glib)** — Core utilities used by Pango/Cairo/librsvg
- **[libxkbcommon](https://xkbcommon.org/)** — Keyboard handling
- **[sdbus-c++](https://github.com/Kistler-Group/sdbus-cpp)** — D-Bus client bindings
- **[libsecret](https://gnome.pages.gitlab.gnome.org/libsecret/)** — Secret Service client for credential and encrypted-state persistence
- **[libsodium](https://doc.libsodium.org/)** — Cryptography for credential and encrypted-state persistence
- **[PipeWire](https://pipewire.org/)** — Audio capture and playback
- **[WirePlumber](https://pipewire.pages.freedesktop.org/wireplumber/)** — PipeWire mixer and default-node integration
- **[libsndfile](https://libsndfile.github.io/libsndfile/)** — UI sound effect decoding
- **[libcurl](https://curl.se/libcurl/)** — HTTP client
- **[libwebp](https://developers.google.com/speed/webp)** — WebP decoding and thumbnail/notification image encoding
- **[libjxl](https://github.com/libjxl/libjxl)** — JPEG XL decoding
- **[libqalculate](https://qalculate.github.io/)** — Calculator engine for the launcher (arithmetic, unit and currency conversion) (GPL-2.0-or-later)
- **[libxml2](https://gitlab.gnome.org/GNOME/libxml2)** — XML parser used to read CalDAV responses (MIT)
- **[libical](https://libical.github.io/libical/)** — iCalendar parsing for calendar events (MPL-2.0)
- **[md4c](https://github.com/mity/md4c)** — CommonMark parser used to render plugin README files (MIT)
- **[nlohmann/json](https://github.com/nlohmann/json)** — JSON for Modern C++ (MIT)
- **[stb](https://github.com/nothings/stb)** — Header-only image resizing and writing utilities (MIT / public domain)
- **[toml++](https://github.com/marzer/tomlplusplus)** — TOML parser (MIT)
- **[polkit](https://gitlab.freedesktop.org/polkit/polkit)** (`polkit-agent`, `polkit-gobject`) — Authentication agent
- **[Linux-PAM](https://github.com/linux-pam/linux-pam)** — Lockscreen authentication
- **[jemalloc](https://jemalloc.net/)** — Optional memory allocator used on glibc builds when detected

## Vendored Libraries

Bundled in `third_party/` and built from source:

- **[fzy](https://github.com/jhawthorn/fzy)** — Fuzzy matching algorithm used by the launcher, search pickers, and other shell ranking (MIT)
- **[Luau](https://luau.org/)** — Lua dialect used for scripting (MIT)
- **[Material Color Utilities](https://github.com/material-foundation/material-color-utilities)** — Material 3 palette generation (Apache-2.0)
- **[Wuffs](https://github.com/google/wuffs)** — Memory-safe image decoders (Apache-2.0)

## System Integration

External tools Hyprbar can integrate with at runtime when present:

- **[ddcutil](https://www.ddcutil.com/)** — External display brightness control

## External services

Hyprbar contacts the endpoints listed in `NETWORK-PRIVACY.md` for community palettes/templates, location lookup,
public-IP lookup, opt-in telemetry, and Google Calendar OAuth. This repository does not establish who currently operates
them or how request data is handled; data-retention practices have not been verified.

## Special Thanks

- The **Wayland** community for building the future of Linux desktop graphics
- The **Niri**, **Hyprland**, **Sway**, **Labwc**, and **MangoWC** teams for their excellent Wayland compositors
- All the contributors and users who have helped make Hyprbar better

## License

Hyprbar is distributed under the MIT license. Source code and bundled third-party components retain their individual licenses;
their license texts are included in `third_party/` and alongside the bundled Tabler font. See [LICENSE](LICENSE) and the
third-party notices.

Each dependency listed above is governed by its own respective license. Please refer to their individual projects for licensing information.
