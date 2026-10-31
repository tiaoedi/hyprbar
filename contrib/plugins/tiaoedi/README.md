# Community plugin snapshots

These plugins are maintained by tiaoedi and are not part of the Hyprbar core runtime or release build. This directory keeps the plugin source and tests alongside the Hyprbar repository for review; install them through the plugin manager or copy the individual plugin directories to `~/.local/share/hyprbar/plugins/`.

- `calculator/`: native `hyprcalculadora`, including its dependency-free arithmetic engine and offline tests. The menu launcher and Hyprland Super+F7 binding are user-level integration and are not installed by the core project.
- `wellbeing/`: reminder widget/panel and singleton service, with translations and offline tests. The Super+F9 binding is user-level integration.

These are source snapshots, not automatically synchronized with the installed plugin copies. Keep changes to a plugin's source, manifest, tests, and README together. Verify with `hyprbar plugins lint <plugin-dir>` and the Lua tests listed in each plugin README before release.

`config-examples/` records the user's Hyprbar TOML, portable calculator desktop launcher, and Hyprland Lua shortcut snippet for reference. Merge TOML settings into an existing configuration instead of blindly replacing it; adapt the Hyprland snippet to the local variable names. The Super+F7 and Super+F9 bindings are already tracked in the user's separate dotfiles repository.
