#pragma once

#include "cli/schema.h"

#include <array>
#include <string_view>

namespace noctalia::cli {

  inline constexpr std::array kConfigValidatePositionals{
      Positional{"path", "Config file or directory; defaults to the active config", {}, false, false, false},
  };
  inline constexpr Command kConfigValidateCmd{
      "validate",
      "Check config validity",
      "With no path, validates the merged configuration the way the shell loads it:\n"
      "  - every *.toml in the active config dir, then\n"
      "  - the state-dir settings.toml overrides.\n\n"
      "With a directory path, validates only that directory's *.toml files.\n"
      "With a file path, validates only that file.\n\n"
      "Reports TOML syntax errors, unknown sections/settings, and bad values\n"
      "(wrong type, out-of-range, invalid enum/color). Exits 1 if any error is found.",
      {},
      {},
      kConfigValidatePositionals,
      {},
      false,
  };

  inline constexpr std::array<std::string_view, 2> kConfigExportModeChoices{"merged", "full"};
  inline constexpr std::array kConfigExportPositionals{
      Positional{"mode", "Export mode (default: merged)", kConfigExportModeChoices, false, false, false},
  };
  inline constexpr Command kConfigExportCmd{
      "export",
      "Print the active config as TOML",
      "Prints TOML to stdout from the same config stack used by the shell:\n"
      "  - every *.toml in the active config dir, then\n"
      "  - the state-dir settings.toml overrides.\n\n"
      "Modes:\n"
      "  merged  Export merged user config only (default)\n"
      "  full    Export full effective config, including built-in defaults",
      {},
      {},
      kConfigExportPositionals,
      {},
      false,
  };

  inline constexpr Command kConfigSettingsCountCmd{
      "settings-count",
      "Count Settings UI controls",
      "Counts one Settings UI row/control per SettingEntry: toggles, sliders, lists,\n"
      "and pickers. Dropdown options and SettingsWindow-only action buttons are not\n"
      "counted separately.",
      {},
      {},
      {},
      {},
      false,
  };

  inline constexpr std::array kConfigImportNoctaliaFlags{
      Flag{"--config-dir", {}, "<dir>", "Legacy configuration source directory", {}, {}, false, false},
      Flag{"--state-dir", {}, "<dir>", "Legacy state source directory", {}, {}, false, false},
      Flag{"--data-dir", {}, "<dir>", "Legacy data source directory", {}, {}, false, false},
      Flag{"--apply", {}, {}, "Write the import into isolated Hyprbar directories", {}, {}, false, false},
      Flag{"--include-local-plugins", {}, {}, "Copy local plugin code from the legacy data directory", {}, {}, false, false},
      Flag{"--include-plugin-data", {}, {}, "Copy persistent plugin data from the legacy state directory", {}, {}, false, false},
  };
  inline constexpr Command kConfigImportNoctaliaCmd{
      "import-noctalia",
      "Import existing configuration",
      "Previews the files to import by default. Pass --apply to write them. Existing target files are never overwritten.\n"
      "Only config TOML files and state/settings.toml are imported by default; app state, notification/clipboard history, and keyring credentials are not copied.\n"
      "Local plugin code and persistent plugin data may be sensitive and are excluded unless their respective --include flags are passed. Imported plugin settings may activate remote plugins on startup; review the files before launching Hyprbar.",
      {},
      kConfigImportNoctaliaFlags,
      {},
      {},
      false,
  };

  inline constexpr std::array kConfigReplayFlags{
      Flag{"--target", {}, "<dir>", "Directory where replay files are written", {}, {}, false, true},
      Flag{"--flattened", {}, {}, "Write only merged_config.content as config.toml", {}, {}, false, false},
      Flag{"--force", {}, {}, "Remove an existing target directory before writing", {}, {}, false, false},
  };
  inline constexpr std::array kConfigReplayPositionals{
      Positional{"report.toml", "Support report to replay", {}, true, false, false},
  };
  inline constexpr Command kConfigReplayReportCmd{
      "replay-report",
      "Reconstruct config and state from a support report",
      "Reconstruct config-home/hyprbar and state-home/hyprbar from a support report.\n\n"
      "With --flattened, reconstruct a single config-home/hyprbar/config.toml from the report's merged config.",
      {},
      kConfigReplayFlags,
      kConfigReplayPositionals,
      {},
      false,
  };

  inline constexpr std::array kConfigSubcommands{
      kConfigExportCmd,
      kConfigImportNoctaliaCmd,
      kConfigReplayReportCmd,
      kConfigSettingsCountCmd,
      kConfigValidateCmd,
  };
  inline constexpr Command kConfigCmd{
      "config", "Validate, export, and import configuration", {}, {}, {}, {}, kConfigSubcommands, false,
  };

} // namespace noctalia::cli
