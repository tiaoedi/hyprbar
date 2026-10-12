# Packaging Hyprbar

Packaging notes for this fork. The source base is Noctalia v5.2.1; upstream source and contributor credits remain in
[`CREDITS.md`](CREDITS.md). Do not treat upstream package listings or repositories as Hyprbar releases.

## Current package status

The repository contains a local Fedora RPM spec at [`packaging/rpm/hyprbar.spec`](packaging/rpm/hyprbar.spec). It is
intended for Fedora 44+ and has not been published to a repository. Other distribution targets have not been validated
for this fork.

Do not publicly redistribute a package carrying the Freedo mark until trademark use has been clarified with FSFLA; see
[`assets/licenses/FREEDO-NOTICE.md`](assets/licenses/FREEDO-NOTICE.md). The artwork is under GFDL 1.3-or-later, and the
full license and attribution notice must ship with it.

## Identity

| Field | Hyprbar value |
|---|---|
| Package | `hyprbar` |
| Version base | `5.2.1` (upstream source version) |
| Executable | `hyprbar` |
| Desktop entry | `dev.hyprbar.Hyprbar.desktop` |
| Icon | `hyprbar` (Freedo artwork) |
| Data | `<prefix>/share/hyprbar/` |
| Code license | MIT; bundled third-party licenses are listed in `CREDITS.md` |
| Freedo license | GFDL 1.3-or-later; separate trademark conditions apply |

## Build and installed layout

Build with Meson and Ninja as described in [`BUILDING.md`](BUILDING.md). Distro builds must not enable native CPU
optimizations. The shipped `assets/` directory is required at runtime; do not package only the executable.

```text
<prefix>/bin/hyprbar
<prefix>/share/hyprbar/assets/...
<prefix>/share/applications/dev.hyprbar.Hyprbar.desktop
<prefix>/share/icons/hicolor/scalable/apps/hyprbar.svg
```

The runtime also supports a portable bundle containing `hyprbar` and `assets/`. Resource lookup is implemented in
`src/core/files/resource_paths.cpp`; `HYPRBAR_ASSETS_DIR` is the explicit asset-root override. Confirm this lookup and
staged install tree whenever changing asset names or Meson install rules.

The RPM spec generates Bash, Zsh, and Fish completions from the freshly built executable. Its `%check` uses isolated
HOME/XDG directories. Build the source archive and RPM using the commands in [`packaging/rpm/README.md`](packaging/rpm/README.md).

## Runtime integrations and compatibility boundary

Hyprbar is a Wayland shell, not a compositor, login manager, or greeter. It can claim freedesktop notification and
StatusNotifier services in sessions where those names are available; avoid running competing hosts at the same time.

Some identifiers intentionally retain their upstream spelling because they are public integration contracts or
persistent formats: the plugin API namespace `noctalia.*`, glyph prefix `noctalia-glyph:`, encrypted-store format
`NOCTALIAENC1`, and optional Noctalia Greeter helper interface. Preserve these until a versioned migration is designed.
Other internal implementation names are not product branding. Do not replace them mechanically: review behavior,
persistence, external consumers, and migration safety first.

Hyprbar's user configuration, state, data, cache, runtime socket, and desktop identity are isolated under Hyprbar-specific
names. The explicit `hyprbar config import-noctalia` command is a migration path: preview is the default, `--apply` is
required to copy, private state is excluded by default, and destination files are never overwritten.
