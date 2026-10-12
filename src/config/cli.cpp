#include "config/cli.h"

#include "cli/help.h"
#include "cli/parse.h"
#include "cli/schema_config.h"
#include "config/config_service.h"
#include "config/config_validate.h"
#include "core/log.h"
#include "core/toml.h" // IWYU pragma: keep
#include "shell/settings/settings_registry.h"
#include "util/file_utils.h"
#include "util/string_utils.h"

#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <expected>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <map>
#include <optional>
#include <print>
#include <string>
#include <string_view>
#include <unistd.h>
#include <vector>

namespace noctalia::config {
  namespace {

    struct ReplayOptions {
      std::filesystem::path reportPath;
      std::filesystem::path targetDir;
      bool flattened = false;
      bool force = false;
    };

    struct SettingsCountSet {
      std::size_t total = 0;
      std::size_t visibleNormal = 0;
      std::size_t visibleAdvanced = 0;
    };

    bool passesVisibility(const Config& cfg, const settings::SettingEntry& entry) {
      return !entry.visibleWhen || entry.visibleWhen(cfg);
    }

    bool visibleWithAdvanced(const Config& cfg, const settings::SettingEntry& entry, bool showAdvanced) {
      return (showAdvanced || !entry.advanced) && passesVisibility(cfg, entry);
    }

    SettingsCountSet countSettingsEntries(const std::vector<settings::SettingEntry>& entries, const Config& cfg) {
      SettingsCountSet out;
      out.total = entries.size();
      for (const auto& entry : entries) {
        if (visibleWithAdvanced(cfg, entry, false)) {
          ++out.visibleNormal;
        }
        if (visibleWithAdvanced(cfg, entry, true)) {
          ++out.visibleAdvanced;
        }
      }
      return out;
    }

    std::size_t countAdvancedMarked(const std::vector<settings::SettingEntry>& entries) {
      return static_cast<std::size_t>(std::ranges::count(entries, true, &settings::SettingEntry::advanced));
    }

    std::size_t countConditionallyHidden(const std::vector<settings::SettingEntry>& entries, const Config& cfg) {
      return static_cast<std::size_t>(std::ranges::count_if(entries, [&](const settings::SettingEntry& entry) {
        return !passesVisibility(cfg, entry);
      }));
    }

    int runSettingsCount(int argc, char* argv[]) {
      auto parsed = cli::parseOrReport(
          cli::kConfigSettingsCountCmd, "hyprbar config settings-count",
          std::span<char* const>{argv + 3, static_cast<std::size_t>(argc - 3)}
      );
      if (!parsed)
        return 1;
      if (parsed->helpRequested)
        return 0;

      setLogLevel(LogLevel::Warn);
      ConfigService configService;
      const Config& cfg = configService.config();
      settings::RegistryEnvironment env;
      std::vector<settings::SettingEntry> registry = settings::buildSettingsRegistry(cfg, nullptr, nullptr, env);
      const SettingsCountSet registryCounts = countSettingsEntries(registry, cfg);

      std::println("Settings controls");
      std::println("Unit: one SettingEntry row/control. Dropdown options are not counted.");
      std::println("Runtime action buttons inserted by SettingsWindow are not counted.");

      std::println();
      std::println("Other totals");
      std::println("  total registry controls:       {}", registryCounts.total);
      std::println("  visible with Advanced off:     {}", registryCounts.visibleNormal);
      std::println("  visible with Advanced on:      {}", registryCounts.visibleAdvanced);
      std::println("  advanced-marked controls:      {}", countAdvancedMarked(registry));
      std::println("  conditionally hidden controls: {}", countConditionallyHidden(registry, cfg));
      std::println(
          "  visible only with Advanced on: {}", registryCounts.visibleAdvanced - registryCounts.visibleNormal
      );

      std::map<std::string, SettingsCountSet> sectionCounts;
      for (const auto& descriptor : settings::settingsSectionDescriptors()) {
        sectionCounts.emplace(std::string(descriptor.id), SettingsCountSet{});
      }
      for (const auto& entry : registry) {
        auto& counts = sectionCounts[std::string(settings::settingsSectionId(entry.section))];
        ++counts.total;
        if (visibleWithAdvanced(cfg, entry, false)) {
          ++counts.visibleNormal;
        }
        if (visibleWithAdvanced(cfg, entry, true)) {
          ++counts.visibleAdvanced;
        }
      }

      std::println();
      std::println("By section");
      std::println("  {:<14} {:>8} {:>8} {:>8}", "section", "total", "normal", "advanced");
      for (const auto& descriptor : settings::settingsSectionDescriptors()) {
        const auto it = sectionCounts.find(std::string(descriptor.id));
        if (it == sectionCounts.end() || it->second.total == 0) {
          continue;
        }
        std::println(
            "  {:<14} {:>8} {:>8} {:>8}", descriptor.id, it->second.total, it->second.visibleNormal,
            it->second.visibleAdvanced
        );
      }

      return 0;
    }

    std::expected<void, std::string> writeTextFile(const std::filesystem::path& path, std::string_view content) {
      std::error_code ec;
      std::filesystem::create_directories(path.parent_path(), ec);
      if (ec) {
        return std::unexpected("failed to create " + path.parent_path().string() + ": " + ec.message());
      }

      std::ofstream out(path, std::ios::binary | std::ios::trunc);
      if (!out.is_open()) {
        return std::unexpected("failed to open " + path.string());
      }
      out.write(content.data(), static_cast<std::streamsize>(content.size()));
      if (!out.good()) {
        return std::unexpected("failed to write " + path.string());
      }
      return {};
    }

    std::optional<std::filesystem::path> safeRelativePath(const toml::table& table, std::string_view fallback) {
      std::string raw;
      if (auto value = table["relative_path"].value<std::string>()) {
        raw = *value;
      } else {
        raw = std::string(fallback);
      }
      if (raw.empty()) {
        return std::nullopt;
      }

      std::filesystem::path path(raw);
      if (path.is_absolute()) {
        return std::nullopt;
      }
      for (const auto& part : path) {
        if (part == "..") {
          return std::nullopt;
        }
      }
      return path.lexically_normal();
    }

    std::expected<void, std::string> prepareTarget(const std::filesystem::path& target, bool force) {
      std::error_code ec;
      if (std::filesystem::exists(target, ec) && !force) {
        return std::unexpected("target already exists; pass --force to replace it: " + target.string());
      }
      std::filesystem::create_directories(target, ec);
      if (ec) {
        return std::unexpected("failed to create target " + target.string() + ": " + ec.message());
      }
      return {};
    }

    int replayReport(const ReplayOptions& options, const char* argv0) {
      toml::table report;
      try {
        report = toml::parse_file(options.reportPath.string());
      } catch (const toml::parse_error& e) {
        std::println(stderr, "error: failed to parse report: {}", e.what());
        return 1;
      }

      const std::filesystem::path target = std::filesystem::absolute(options.targetDir).lexically_normal();
      if (auto prepared = prepareTarget(target, options.force); !prepared) {
        std::println(stderr, "error: {}", prepared.error());
        return 1;
      }

      const std::filesystem::path configHome = target / "config-home";
      const std::filesystem::path stateHome = target / "state-home";
      const std::filesystem::path configDir = configHome / "hyprbar";
      const std::filesystem::path stateDir = stateHome / "hyprbar";

      if (options.force) {
        std::error_code ec;
        std::filesystem::remove_all(configHome, ec);
        if (ec) {
          std::println(stderr, "error: failed to remove {}: {}", configHome.string(), ec.message());
          return 1;
        }
        std::filesystem::remove_all(stateHome, ec);
        if (ec) {
          std::println(stderr, "error: failed to remove {}: {}", stateHome.string(), ec.message());
          return 1;
        }
      }

      if (options.flattened) {
        const auto merged = report["merged_config"]["content"].value<std::string>();
        if (!merged.has_value()) {
          std::println(stderr, "error: report has no [merged_config].content");
          return 1;
        }
        if (auto written = writeTextFile(configDir / "config.toml", *merged); !written) {
          std::println(stderr, "error: {}", written.error());
          return 1;
        }
        std::error_code ec;
        std::filesystem::create_directories(stateDir, ec);
        if (ec) {
          std::println(stderr, "error: failed to create {}: {}", stateDir.string(), ec.message());
          return 1;
        }
      } else {
        const auto* sources = report["config_sources"].as_array();
        if (sources != nullptr) {
          std::size_t fallbackIndex = 0;
          for (const auto& sourceNode : *sources) {
            const auto* source = sourceNode.as_table();
            if (source == nullptr) {
              continue;
            }
            const auto content = (*source)["content"].value<std::string>();
            if (!content.has_value()) {
              continue;
            }

            const auto relative = safeRelativePath(*source, "config_" + std::to_string(fallbackIndex++) + ".toml");
            if (!relative.has_value()) {
              std::println(stderr, "error: report contains an unsafe config source path");
              return 1;
            }
            if (auto written = writeTextFile(configDir / *relative, *content); !written) {
              std::println(stderr, "error: {}", written.error());
              return 1;
            }
          }
        }

        const auto* state = report["state_settings"].as_table();
        bool stateExists = state != nullptr;
        if (state != nullptr) {
          if (auto exists = (*state)["exists"].value<bool>()) {
            stateExists = *exists;
          }
        }
        if (stateExists && state != nullptr) {
          const auto content = (*state)["content"].value<std::string>().value_or("");
          if (auto written = writeTextFile(stateDir / "settings.toml", content); !written) {
            std::println(stderr, "error: {}", written.error());
            return 1;
          }
        } else {
          std::error_code ec;
          std::filesystem::create_directories(stateDir, ec);
          if (ec) {
            std::println(stderr, "error: failed to create {}: {}", stateDir.string(), ec.message());
            return 1;
          }
        }

        const auto* appState = report["app_state"].as_table();
        bool appStateExists = appState != nullptr;
        if (appState != nullptr) {
          if (auto exists = (*appState)["exists"].value<bool>()) {
            appStateExists = *exists;
          }
        }
        if (appStateExists && appState != nullptr) {
          const auto content = (*appState)["content"].value<std::string>().value_or("");
          if (auto written = writeTextFile(stateDir / "state.toml", content); !written) {
            std::println(stderr, "error: {}", written.error());
            return 1;
          }
        }
      }

      std::println("Replayed support report into {}", target.string());
      std::println();
      std::println("Config home: {}", configHome.string());
      std::println("State home:  {}", stateHome.string());
      std::println();
      std::println("Run with:");
      std::println(
          "  HYPRBAR_CONFIG_HOME={} HYPRBAR_STATE_HOME={} {}", StringUtils::shellQuote(configHome.string()),
          StringUtils::shellQuote(stateHome.string()), StringUtils::shellQuote(argv0)
      );
      return 0;
    }

    // ANSI color only when the stream is a terminal and NO_COLOR is unset, so
    // piped/redirected output stays clean.
    bool useColor(std::FILE* stream) {
      static const bool noColor = std::getenv("NO_COLOR") != nullptr;
      return !noColor && isatty(fileno(stream)) != 0;
    }

    int runValidate(int argc, char* argv[]) {
      auto parsed = cli::parseOrReport(
          cli::kConfigValidateCmd, "hyprbar config validate",
          std::span<char* const>{argv + 3, static_cast<std::size_t>(argc - 3)}
      );
      if (!parsed)
        return 1;
      if (parsed->helpRequested)
        return 0;
      const std::string pathArg =
          parsed->positionals.empty() ? std::string{} : std::string(parsed->positionals.front());

      // Validation reports through diagnostics below; silence incidental INFO logs
      // (e.g. the plugin registry scan) so only validation results reach the user.
      setLogLevel(LogLevel::Warn);
      schema::Diagnostics diagnostics;

      if (pathArg.empty()) {
        const std::string configDir = FileUtils::configDir();
        std::string settingsPath;
        if (const std::string stateDir = FileUtils::stateDir(); !stateDir.empty()) {
          settingsPath = stateDir + "/settings.toml";
        }
        diagnostics = validateConfigSources(configDir, settingsPath);
      } else {
        std::error_code ec;
        const std::filesystem::path inputPath(pathArg);
        const auto status = std::filesystem::status(inputPath, ec);
        if (ec) {
          std::println(stderr, "error: failed to inspect {}: {}", pathArg, ec.message());
          return 1;
        }
        if (std::filesystem::is_directory(status)) {
          diagnostics = validateConfigSources(pathArg, {});
        } else if (std::filesystem::is_regular_file(status)) {
          diagnostics = validateConfigFile(pathArg);
        } else {
          std::println(stderr, "error: path is not a regular file or directory: {}", pathArg);
          return 1;
        }
      }

      const bool colorErr = useColor(stderr);
      const bool colorOut = useColor(stdout);

      std::size_t errors = 0;
      std::size_t warnings = 0;
      for (const auto& entry : diagnostics.entries) {
        const bool isError = entry.severity == schema::Diagnostics::Severity::Error;
        (isError ? errors : warnings)++;
        std::FILE* out = isError ? stderr : stdout;
        const char* tag = isError ? "ERROR" : "WARN "; // padded to align the path column
        const char* color = (isError ? colorErr : colorOut) ? (isError ? "\033[31m" : "\033[33m") : "";
        const char* reset = *color != '\0' ? "\033[0m" : "";
        const std::string location = entry.origin.valid() ? entry.origin.format() + ": " : std::string{};
        std::println(out, "{}{}{} {}{}: {}", color, tag, reset, location, entry.path, entry.message);
      }

      if (errors > 0) {
        const char* c = colorErr ? "\033[31m" : "";
        const char* r = colorErr ? "\033[0m" : "";
        std::println(stderr);
        std::println(stderr, "{}✗ Config is invalid{} ({} error(s), {} warning(s))", c, r, errors, warnings);
        return 1;
      }
      const char* c = colorOut ? "\033[32m" : "";
      const char* r = colorOut ? "\033[0m" : "";
      if (warnings > 0) {
        std::println();
        std::println("{}✓ Config is valid{} ({} warning(s))", c, r, warnings);
      } else {
        std::println("{}✓ Config is valid{}", c, r);
      }
      return 0;
    }

    int runExport(int argc, char* argv[]) {
      auto parsed = cli::parseOrReport(
          cli::kConfigExportCmd, "hyprbar config export",
          std::span<char* const>{argv + 3, static_cast<std::size_t>(argc - 3)}
      );
      if (!parsed)
        return 1;
      if (parsed->helpRequested)
        return 0;
      const std::string_view mode =
          parsed->positionals.empty() ? std::string_view{"merged"} : parsed->positionals.front();

      const std::string configDir = FileUtils::configDir();
      std::string settingsPath;
      if (const std::string stateDir = FileUtils::stateDir(); !stateDir.empty()) {
        settingsPath = stateDir + "/settings.toml";
      }

      std::string error;
      std::string content;
      if (mode == "merged") {
        content = ConfigService::buildMergedUserConfigFromSources(configDir, settingsPath, &error);
      } else if (mode == "full") {
        content = ConfigService::buildEffectiveConfigFromSources(configDir, settingsPath, &error);
      } else {
        std::println(stderr, "error: expected merged or full");
        return 1;
      }

      if (!error.empty()) {
        std::println(stderr, "error: {}", error);
        return 1;
      }

      std::fputs(content.c_str(), stdout);
      return 0;
    }

    struct ImportFile {
      std::filesystem::path source;
      std::filesystem::path target;
      std::filesystem::path relative;
      std::string kind;
    };

    std::expected<std::filesystem::path, std::string> absolutePath(std::filesystem::path path) {
      if (path.empty()) {
        return std::unexpected("path is empty");
      }
      path = FileUtils::expandUserPath(path.string());
      std::error_code ec;
      path = std::filesystem::absolute(path, ec);
      if (ec) {
        return std::unexpected("failed to resolve path: " + ec.message());
      }
      return path.lexically_normal();
    }

    std::expected<std::filesystem::path, std::string> comparisonPath(const std::filesystem::path& path) {
      std::error_code ec;
      auto resolved = std::filesystem::weakly_canonical(path, ec);
      if (ec) {
        return std::unexpected("failed to resolve import directory for overlap check: " + ec.message());
      }
      return resolved;
    }

    std::filesystem::path defaultNoctaliaDir(const char* xdgEnv, std::string_view fallback) {
      const char* xdg = std::getenv(xdgEnv);
      std::filesystem::path base;
      if (xdg != nullptr && xdg[0] != '\0') {
        base = xdg;
      } else if (const char* home = std::getenv("HOME"); home != nullptr && home[0] != '\0') {
        base = std::filesystem::path(home) / fallback;
      }
      return base.empty() ? std::filesystem::path{} : base / "noctalia";
    }

    bool isWithin(const std::filesystem::path& child, const std::filesystem::path& parent) {
      const auto relative = child.lexically_relative(parent);
      if (relative.empty() || relative == ".") {
        return true;
      }
      return !relative.is_absolute() && *relative.begin() != "..";
    }

    bool pathsOverlap(const std::filesystem::path& first, const std::filesystem::path& second) {
      return isWithin(first, second) || isWithin(second, first);
    }

    std::expected<void, std::string> validateSeparateRoots(
        const std::vector<std::filesystem::path>& sourceRoots,
        const std::vector<std::filesystem::path>& targetRoots
    ) {
      for (const auto& sourceRoot : sourceRoots) {
        auto resolvedSource = comparisonPath(sourceRoot);
        if (!resolvedSource) {
          return std::unexpected(resolvedSource.error());
        }
        for (const auto& targetRoot : targetRoots) {
          auto resolvedTarget = comparisonPath(targetRoot);
          if (!resolvedTarget) {
            return std::unexpected(resolvedTarget.error());
          }
          if (pathsOverlap(*resolvedSource, *resolvedTarget)) {
            return std::unexpected("Source and target directories must not overlap");
          }
        }
      }
      return {};
    }

    std::expected<std::filesystem::path, std::string> resolveImportSymlink(
        const std::filesystem::path& sourceRoot, const std::filesystem::path& sourceFile
    ) {
      std::error_code ec;
      const auto canonicalRoot = std::filesystem::canonical(sourceRoot, ec);
      if (ec) {
        return std::unexpected("failed to resolve source directory " + sourceRoot.string() + ": " + ec.message());
      }
      const auto canonicalFile = std::filesystem::canonical(sourceFile, ec);
      if (ec) {
        return std::unexpected("failed to resolve symlink " + sourceFile.string() + ": " + ec.message());
      }
      const bool isRegular = std::filesystem::is_regular_file(canonicalFile, ec);
      if (ec || !isRegular) {
        return std::unexpected("symlink does not resolve to a regular file: " + sourceFile.string());
      }
      if (!isWithin(canonicalFile, canonicalRoot)) {
        return std::unexpected("symlink target is outside source directory: " + sourceFile.string());
      }
      return canonicalFile;
    }

    std::expected<std::vector<ImportFile>, std::string> collectImportTree(
        const std::filesystem::path& sourceRoot, const std::filesystem::path& targetRoot,
        std::string_view kind, bool tomlOnly
    ) {
      std::error_code ec;
      const auto rootStatus = std::filesystem::symlink_status(sourceRoot, ec);
      if (ec || !std::filesystem::is_directory(rootStatus) || std::filesystem::is_symlink(rootStatus)) {
        return std::unexpected("source directory is missing, not a directory, or a symlink: " + sourceRoot.string());
      }

      std::vector<ImportFile> files;
      std::filesystem::recursive_directory_iterator it(sourceRoot, std::filesystem::directory_options::none, ec);
      const std::filesystem::recursive_directory_iterator end;
      if (ec) {
        return std::unexpected("failed to scan source directory " + sourceRoot.string() + ": " + ec.message());
      }
      for (; it != end; it.increment(ec)) {
        if (ec) {
          return std::unexpected("failed while scanning " + sourceRoot.string() + ": " + ec.message());
        }
        const auto status = it->symlink_status(ec);
        if (ec) {
          return std::unexpected("failed to inspect " + it->path().string() + ": " + ec.message());
        }
        if (std::filesystem::is_symlink(status)) {
          if (!tomlOnly) {
            return std::unexpected("refusing to import symlink: " + it->path().string());
          }
          if (it->path().extension() == ".toml") {
            auto resolved = resolveImportSymlink(sourceRoot, it->path());
            if (!resolved) {
              return std::unexpected("config " + resolved.error());
            }
            const auto relative = it->path().lexically_relative(sourceRoot).lexically_normal();
            files.push_back(ImportFile{
                .source = std::move(*resolved),
                .target = targetRoot / relative,
                .relative = relative,
                .kind = std::string(kind) + " symlink target",
            });
          }
          continue;
        }
        if (!std::filesystem::is_regular_file(status) || (tomlOnly && it->path().extension() != ".toml")) {
          continue;
        }
        const auto relative = it->path().lexically_relative(sourceRoot).lexically_normal();
        if (relative.empty() || relative.is_absolute()
            || std::ranges::any_of(relative, [](const auto& part) { return part == ".."; })) {
          return std::unexpected("unsafe relative source path: " + it->path().string());
        }
        files.push_back(ImportFile{
            .source = it->path(), .target = targetRoot / relative, .relative = relative, .kind = std::string(kind),
        });
      }
      if (ec) {
        return std::unexpected("failed while scanning " + sourceRoot.string() + ": " + ec.message());
      }
      std::ranges::sort(files, {}, &ImportFile::relative);
      return files;
    }

    std::expected<void, std::string> validateImportTarget(
        const std::filesystem::path& path,
        const std::vector<std::filesystem::path>& sourceRoots
    ) {
      std::error_code ec;
      const auto status = std::filesystem::symlink_status(path, ec);
      if (ec == std::errc::no_such_file_or_directory) {
        ec.clear();
      } else if (ec) {
        return std::unexpected("failed to inspect target " + path.string() + ": " + ec.message());
      } else if (std::filesystem::exists(status)) {
        return std::unexpected("target already exists; import will not overwrite it: " + path.string());
      }

      auto resolvedTarget = comparisonPath(path);
      if (!resolvedTarget) {
        return std::unexpected(resolvedTarget.error());
      }
      for (const auto& sourceRoot : sourceRoots) {
        auto resolvedSource = comparisonPath(sourceRoot);
        if (!resolvedSource) {
          return std::unexpected(resolvedSource.error());
        }
        if (pathsOverlap(*resolvedTarget, *resolvedSource)) {
          return std::unexpected("import target overlaps a legacy source directory: " + path.string());
        }
      }
      return {};
    }

    bool createImportDirectories(
        const std::filesystem::path& targetParent,
        std::vector<std::filesystem::path>& createdDirectories,
        std::error_code& ec
    ) {
      std::vector<std::filesystem::path> missingDirectories;
      for (auto current = targetParent; !current.empty();) {
        ec.clear();
        if (std::filesystem::is_directory(current, ec)) {
          break;
        }
        if (ec && ec != std::errc::no_such_file_or_directory) {
          return false;
        }

        ec.clear();
        const auto linkStatus = std::filesystem::symlink_status(current, ec);
        if (ec == std::errc::no_such_file_or_directory
            || (!ec && linkStatus.type() == std::filesystem::file_type::not_found)) {
          ec.clear();
          missingDirectories.push_back(current);
        } else if (ec) {
          return false;
        } else {
          ec = std::make_error_code(std::errc::not_a_directory);
          return false;
        }

        const auto parent = current.parent_path();
        if (parent == current) {
          ec = std::make_error_code(std::errc::not_a_directory);
          return false;
        }
        current = parent;
      }

      std::ranges::reverse(missingDirectories);
      for (const auto& directory : missingDirectories) {
        const bool created = std::filesystem::create_directory(directory, ec);
        if (ec) {
          return false;
        }
        if (created) {
          createdDirectories.push_back(directory);
          continue;
        }

        if (!std::filesystem::is_directory(directory, ec) || ec) {
          if (!ec) {
            ec = std::make_error_code(std::errc::not_a_directory);
          }
          return false;
        }
      }
      return true;
    }

    int runImportNoctalia(int argc, char* argv[]) {
      auto parsed = cli::parseOrReport(
          cli::kConfigImportNoctaliaCmd, "hyprbar config import-noctalia",
          std::span<char* const>{argv + 3, static_cast<std::size_t>(argc - 3)}
      );
      if (!parsed)
        return 1;
      if (parsed->helpRequested)
        return 0;

      auto sourceConfig = absolutePath(parsed->value("--config-dir").empty()
          ? defaultNoctaliaDir("XDG_CONFIG_HOME", ".config")
          : std::filesystem::path(parsed->value("--config-dir")));
      auto sourceState = absolutePath(parsed->value("--state-dir").empty()
          ? defaultNoctaliaDir("XDG_STATE_HOME", ".local/state")
          : std::filesystem::path(parsed->value("--state-dir")));
      auto sourceData = absolutePath(parsed->value("--data-dir").empty()
          ? defaultNoctaliaDir("XDG_DATA_HOME", ".local/share")
          : std::filesystem::path(parsed->value("--data-dir")));
      auto targetConfig = absolutePath(FileUtils::configDir());
      auto targetState = absolutePath(FileUtils::stateDir());
      auto targetData = absolutePath(FileUtils::dataDir());
      if (!sourceConfig || !sourceState || !sourceData || !targetConfig || !targetState || !targetData) {
        const std::string reason = !sourceConfig ? sourceConfig.error()
            : !sourceState                     ? sourceState.error()
            : !sourceData                      ? sourceData.error()
            : !targetConfig                    ? targetConfig.error()
            : !targetState                     ? targetState.error()
                                               : targetData.error();
        std::println(stderr, "error: {}", reason);
        return 1;
      }

      std::vector<std::filesystem::path> sourceRoots{*sourceConfig, *sourceState};
      std::vector<std::filesystem::path> targetRoots{*targetConfig, *targetState};
      if (parsed->has("--include-local-plugins")) {
        sourceRoots.push_back(*sourceData);
        targetRoots.push_back(*targetData);
      }
      if (auto separate = validateSeparateRoots(sourceRoots, targetRoots); !separate) {
        std::println(stderr, "error: {}", separate.error());
        return 1;
      }

      auto configFiles = collectImportTree(*sourceConfig, *targetConfig, "config", true);
      if (!configFiles) {
        std::println(stderr, "error: {}", configFiles.error());
        return 1;
      }
      std::vector<ImportFile> files = std::move(*configFiles);

      const auto sourceSettings = *sourceState / "settings.toml";
      std::error_code ec;
      const auto settingsLinkStatus = std::filesystem::symlink_status(sourceSettings, ec);
      if (ec && ec != std::errc::no_such_file_or_directory) {
        std::println(stderr, "error: failed to inspect {}: {}", sourceSettings.string(), ec.message());
        return 1;
      }
      std::string settingsKind = "settings";
      std::filesystem::path settingsSource = sourceSettings;
      if (!ec && std::filesystem::is_symlink(settingsLinkStatus)) {
        auto resolved = resolveImportSymlink(*sourceState, sourceSettings);
        if (!resolved) {
          std::println(stderr, "error: settings {}", resolved.error());
          return 1;
        }
        settingsSource = std::move(*resolved);
        settingsKind += " symlink target";
      }
      if (!ec && (std::filesystem::is_regular_file(settingsLinkStatus) || std::filesystem::is_symlink(settingsLinkStatus))) {
        files.push_back(ImportFile{
            .source = std::move(settingsSource),
            .target = *targetState / "settings.toml",
            .relative = "settings.toml",
            .kind = std::move(settingsKind),
        });
      }

      if (parsed->has("--include-local-plugins")) {
        const auto sourcePlugins = *sourceData / "plugins";
        const auto targetPlugins = *targetData / "plugins";
        if (isWithin(targetPlugins, sourcePlugins) || isWithin(sourcePlugins, targetPlugins)) {
          std::println(stderr, "error: source and target plugin directories must be separate");
          return 1;
        }
        if (std::filesystem::exists(sourcePlugins, ec) && !ec) {
          auto pluginFiles = collectImportTree(sourcePlugins, targetPlugins, "local plugin", false);
          if (!pluginFiles) {
            std::println(stderr, "error: {}", pluginFiles.error());
            return 1;
          }
          files.insert(files.end(), std::make_move_iterator(pluginFiles->begin()), std::make_move_iterator(pluginFiles->end()));
        } else if (ec) {
          std::println(stderr, "error: failed to inspect {}: {}", sourcePlugins.string(), ec.message());
          return 1;
        }
      }

      if (parsed->has("--include-plugin-data")) {
        const auto sourcePluginData = *sourceState / "plugins/data";
        const auto targetPluginData = *targetState / "plugins/data";
        if (isWithin(targetPluginData, sourcePluginData) || isWithin(sourcePluginData, targetPluginData)) {
          std::println(stderr, "error: source and target plugin data directories must be separate");
          return 1;
        }
        if (std::filesystem::exists(sourcePluginData, ec) && !ec) {
          auto pluginDataFiles = collectImportTree(sourcePluginData, targetPluginData, "plugin data", false);
          if (!pluginDataFiles) {
            std::println(stderr, "error: {}", pluginDataFiles.error());
            return 1;
          }
          files.insert(files.end(), std::make_move_iterator(pluginDataFiles->begin()), std::make_move_iterator(pluginDataFiles->end()));
        } else if (ec) {
          std::println(stderr, "error: failed to inspect {}: {}", sourcePluginData.string(), ec.message());
          return 1;
        }
      }

      if (files.empty()) {
        std::println(stderr, "error: no importable config, settings, or local plugin files were found");
        return 1;
      }
      for (const auto& file : files) {
        if (auto valid = validateImportTarget(file.target, sourceRoots); !valid) {
          std::println(stderr, "error: {}", valid.error());
          return 1;
        }
      }

      std::println("{} {} file(s):", parsed->has("--apply") ? "Importing" : "Previewing", files.size());
      for (const auto& file : files) {
        std::println("  {}: {} -> {}", file.kind, file.source.string(), file.target.string());
      }
      if (!parsed->has("--apply")) {
        std::println("Preview only; pass --apply to copy these files. No source or target files were changed.");
        return 0;
      }

      std::vector<std::filesystem::path> copied;
      std::vector<std::filesystem::path> createdDirectories;
      for (const auto& file : files) {
        if (!createImportDirectories(file.target.parent_path(), createdDirectories, ec)) {
          break;
        }
        if (!std::filesystem::copy_file(file.source, file.target, std::filesystem::copy_options::none, ec)) {
          if (!ec) {
            ec = std::make_error_code(std::errc::io_error);
          }
          break;
        }
        copied.push_back(file.target);
        std::filesystem::permissions(file.target, FileUtils::privateFileMode(), std::filesystem::perm_options::replace, ec);
        if (ec) {
          break;
        }
      }
      if (ec) {
        const std::string message = ec.message();
        bool rollbackComplete = true;
        for (const auto& path : copied) {
          std::error_code cleanupError;
          std::filesystem::remove(path, cleanupError);
          rollbackComplete = rollbackComplete && !cleanupError;
        }
        for (auto directory = createdDirectories.rbegin(); directory != createdDirectories.rend(); ++directory) {
          std::error_code cleanupError;
          std::filesystem::remove(*directory, cleanupError);
          rollbackComplete = rollbackComplete && !cleanupError;
        }
        if (rollbackComplete) {
          std::println(stderr, "error: import failed and copied files were rolled back: {}", message);
        } else {
          std::println(stderr, "error: import failed and rollback was incomplete: {}", message);
        }
        return 1;
      }

      std::println("Imported {} file(s) into Hyprbar's isolated directories. Source files were left unchanged.", files.size());
      std::println("Keyring credentials, app state, plugin caches, notification history, and clipboard history were not copied.");
      if (parsed->has("--include-local-plugins")) {
        std::println("Local plugin code was copied; review it before starting Hyprbar.");
      }
      if (parsed->has("--include-plugin-data")) {
        std::println("Persistent plugin data was copied; treat it as potentially sensitive.");
      }
      return 0;
    }

  } // namespace

  int runCli(int argc, char* argv[]) {
    if (argc < 3 || std::strcmp(argv[2], "--help") == 0 || std::strcmp(argv[2], "-h") == 0) {
      std::print("{}", cli::renderHelp(cli::kConfigCmd, "hyprbar config"));
      return argc < 3 ? 1 : 0;
    }

    if (std::strcmp(argv[2], "validate") == 0)
      return runValidate(argc, argv);
    if (std::strcmp(argv[2], "import-noctalia") == 0)
      return runImportNoctalia(argc, argv);
    if (std::strcmp(argv[2], "export") == 0)
      return runExport(argc, argv);
    if (std::strcmp(argv[2], "settings-count") == 0)
      return runSettingsCount(argc, argv);
    if (std::strcmp(argv[2], "replay-report") == 0) {
      auto parsed = cli::parseOrReport(
          cli::kConfigReplayReportCmd, "hyprbar config replay-report",
          std::span<char* const>{argv + 3, static_cast<std::size_t>(argc - 3)}
      );
      if (!parsed)
        return 1;
      if (parsed->helpRequested)
        return 0;
      ReplayOptions options{
          .reportPath = parsed->positionals.front(),
          .targetDir = parsed->value("--target"),
          .flattened = parsed->has("--flattened"),
          .force = parsed->has("--force"),
      };
      return replayReport(options, argv[0]);
    }

    std::println(stderr, "error: unknown command: {}", argv[2]);
    std::println(stderr, "Run 'hyprbar config --help' for usage.");
    return 1;
  }

} // namespace noctalia::config
