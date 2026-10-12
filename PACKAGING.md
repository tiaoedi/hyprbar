# Packaging Hyprbar

Hyprbar is an independent fork based on Noctalia v5.2.1. Upstream source and contributor credits are retained in [`CREDITS.md`](CREDITS.md). Do not treat upstream package repositories as Hyprbar releases.

## Current package status

No prebuilt package or checksum is published yet. The RPM spec targets Fedora 44 x86_64; package build/install verification is tracked separately from the successful source build and test run. Other distributions have not been validated.

## Identity

| Field | Hyprbar value |
|---|---|
| Package | `hyprbar` |
| Version base | `5.2.1` (upstream source version) |
| Executable | `hyprbar` |
| Desktop entry | `dev.hyprbar.Hyprbar.desktop` |
| Icon | `hyprbar` (original Hyprbar vector artwork) |
| Data | `<prefix>/share/hyprbar/` |
| License | MIT for the upstream source; bundled components retain their own licenses |
| Nix / Guix | Package definitions are not included or verified in this fork |

## Build and installed layout

Build with Meson and Ninja as described in [`BUILDING.md`](BUILDING.md). Distribution builds must not enable native CPU optimizations. The complete `assets/` directory is required at runtime; do not package only the executable.

```text
<prefix>/bin/hyprbar
<prefix>/share/hyprbar/assets/...
<prefix>/share/applications/dev.hyprbar.Hyprbar.desktop
<prefix>/share/icons/hicolor/scalable/apps/hyprbar.svg
```

The runtime also supports a portable bundle containing `hyprbar` and `assets/`. Asset lookup is implemented in `src/core/files/resource_paths.cpp`; `HYPRBAR_ASSETS_DIR` is the explicit asset-root override. Confirm this lookup and the staged install tree whenever asset names or Meson install rules change.

The RPM spec generates Bash, Zsh, and Fish completions from the freshly built executable. Its `%check` uses isolated HOME/XDG directories. See [`packaging/rpm/README.md`](packaging/rpm/README.md) for source archive and build commands.

## Runtime integrations and compatibility boundary

Hyprbar is a Wayland shell, not a compositor, login manager, or greeter. It may claim freedesktop notification and StatusNotifier services; avoid running competing hosts for those services in the same session.

Some identifiers intentionally retain upstream spelling because they are public integration contracts or persistent formats: plugin API namespace `noctalia.*`, glyph prefix `noctalia-glyph:`, encrypted-store format `NOCTALIAENC1`, and the optional Noctalia Greeter helper interface. Preserve these until a versioned migration is designed. Other internal implementation names are not product branding; review behavior, persistence, external consumers, and migration safety before changing them.

Hyprbar configuration, state, data, cache, runtime socket, and desktop identity use Hyprbar-specific names. `hyprbar config import-noctalia` is an explicit migration path: preview is the default, `--apply` is required to copy, private state is excluded by default, and destination files are not overwritten.
