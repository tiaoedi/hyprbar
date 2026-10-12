# Hyprbar

Hyprbar is a native Wayland desktop shell for a configurable Linux desktop. It brings together bars, widgets, dock,
launcher, control center, notifications, wallpaper, lock screen, session actions, clipboard history, OSDs, tray integration,
and desktop widgets.

It runs directly on Wayland and OpenGL ES, without Qt or GTK. Hyprbar is based on the Noctalia v5.2.1 source project;
upstream notices and contributor credits are retained in [`CREDITS.md`](CREDITS.md) and the source license.

<p align="center">
  <img src="assets/freedo.svg" alt="Freedo, the GNU Linux-libre mascot" width="180" />
</p>

The Freedo artwork is separately licensed under GFDL 1.3-or-later and is a trademark of GNU Linux-libre. See
[`assets/licenses/FREEDO-NOTICE.md`](assets/licenses/FREEDO-NOTICE.md). The notice must be clarified with FSFLA before
public redistribution of builds carrying the mark.

## Features

- Multi-monitor bars, taskbar, workspaces, tray, media, network, battery, brightness, weather, clipboard, and custom widgets.
- Dock, launcher, control center, notifications, wallpaper picker, OSDs, lock screen, session panel, and desktop widgets.
- TOML configuration with hot reload, GUI-managed overrides, themes, templates, and runtime IPC.
- Wayland integration for layer-shell, session lock, idle behavior, clipboard, foreign toplevels, workspaces, and fractional scaling.
- Compositor integrations including Niri, Hyprland, Sway, Scroll, Mango, Labwc, and dwl, with capabilities depending on compositor protocols and IPC.

Hyprbar is a desktop shell, not a compositor or full desktop environment. Window management, login management, file
management, removable-drive mounting, printers, and screen casting remain the responsibility of other system components.

## Build and test

See [`BUILDING.md`](BUILDING.md) for source dependencies and build commands. Fedora RPM packaging is documented in
[`packaging/rpm/README.md`](packaging/rpm/README.md). The package currently has no public repository; the local RPM is
for isolated testing only.

Configuration and feature references are in [`docs/user/`](docs/user/). Plugin scripts retain the upstream `noctalia.*`
runtime API namespace for compatibility; see the plugin documentation before reusing upstream plugins.

## License and attribution

Hyprbar source code is licensed under the MIT License; bundled dependencies have their own notices. Freedo artwork has
separate GFDL terms and trademark conditions. See [`LICENSE`](LICENSE), [`CREDITS.md`](CREDITS.md), and
[`assets/licenses/`](assets/licenses/) before redistribution.
