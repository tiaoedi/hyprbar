// A requested after-apply notification is owed until an application delivers it. Later
// applies that coalesce with, supersede, or deduplicate against the requesting one must not
// swallow it, and an application that did not ask for one must stay silent.

#include "config/config_service.h"
#include "core/deferred_call.h"
#include "tests/test_check.h"
#include "theme/app_colors_changed.h"
#include "theme/palette.h"
#include "theme/template_apply_service.h"

#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <optional>
#include <string>
#include <string_view>
#include <thread>
#include <unistd.h>

namespace {

  using noctalia::theme::GeneratedPalette;
  using noctalia::theme::TemplateApplyService;

  GeneratedPalette paletteWith(std::uint32_t surface) {
    GeneratedPalette palette;
    palette.dark["mSurface"] = surface;
    palette.light["mSurface"] = surface;
    return palette;
  }

  // The worker applies once the request stream has been quiet for its coalescing window and
  // posts the notification through the deferred-call queue the main loop drains.
  void settle() {
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(400);
    while (std::chrono::steady_clock::now() < deadline) {
      for (auto& call : DeferredCall::takePending()) {
        call();
      }
      std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
    for (auto& call : DeferredCall::takePending()) {
      call();
    }
  }

} // namespace

int main() {
  const std::filesystem::path root =
      std::filesystem::temp_directory_path() / ("noctalia-template-notify-" + std::to_string(::getpid()));
  std::filesystem::remove_all(root);
  std::filesystem::create_directories(root / "config");
  std::filesystem::create_directories(root / "state");
  std::filesystem::create_directories(root / "data");
  ::setenv("HYPRBAR_CONFIG_HOME", (root / "config").c_str(), 1);
  ::setenv("HYPRBAR_STATE_HOME", (root / "state").c_str(), 1);
  ::setenv("HYPRBAR_DATA_HOME", (root / "data").c_str(), 1);

  int applications = 0;
  int paletteChanges = 0;
  std::string lastMode;
  {
    ConfigService config;
    TemplateApplyService service(config);
    service.setAfterApplyCallback([&](std::string_view appliedMode, bool paletteChanged) {
      ++applications;
      paletteChanges += paletteChanged ? 1 : 0;
      lastMode = appliedMode;
    });

    // A plain application that changed the palette.
    service.apply(paletteWith(0x111111), "dark", /*force=*/false, /*paletteChanged=*/true);
    settle();
    TEST_CHECK(applications == 1);
    TEST_CHECK(paletteChanges == 1);
    TEST_CHECK(lastMode == "dark");

    // A same-palette apply deduplicates against the queued one. It must not cancel the palette
    // change the queued one is still owed.
    applications = 0;
    paletteChanges = 0;
    service.apply(paletteWith(0x222222), "dark", /*force=*/false, /*paletteChanged=*/true);
    service.apply(paletteWith(0x222222), "dark", /*force=*/false, /*paletteChanged=*/false);
    settle();
    TEST_CHECK(applications == 1);
    TEST_CHECK(paletteChanges == 1);

    // A different palette supersedes the queued request before it runs. The superseding
    // generation inherits the owed palette change instead of dropping it.
    applications = 0;
    paletteChanges = 0;
    service.apply(paletteWith(0x333333), "dark", /*force=*/false, /*paletteChanged=*/true);
    service.apply(paletteWith(0x444444), "dark", /*force=*/false, /*paletteChanged=*/false);
    settle();
    TEST_CHECK(applications == 1);
    TEST_CHECK(paletteChanges == 1);

    // An application that only switched mode still reports, so a consumer ordered behind the
    // templates runs, but it is not a palette change.
    applications = 0;
    paletteChanges = 0;
    service.apply(paletteWith(0x444444), "light", /*force=*/false, /*paletteChanged=*/false);
    settle();
    TEST_CHECK(applications == 1);
    TEST_CHECK(paletteChanges == 0);
    TEST_CHECK(lastMode == "light");

    // A palette change owed by an apply that has nothing left to render still lands.
    applications = 0;
    paletteChanges = 0;
    service.apply(paletteWith(0x444444), "light", /*force=*/false, /*paletteChanged=*/true);
    settle();
    TEST_CHECK(applications == 1);
    TEST_CHECK(paletteChanges == 1);
  }

  // Exercise the same notification predicate used by the resolved callback with an unchanged
  // dual palette. The app mode selects a different rendered output, and colors_changed must
  // see that output, not the old generation. Everything stays inside the isolated test root.
  std::filesystem::create_directories(root / "state" / "hyprbar");
  const auto input = root / "app-colors.tmpl";
  const auto output = root / "app-colors.out";
  {
    std::ofstream out(input);
    out << "{{colors.surface.default.hex}}";
  }
  {
    std::ofstream out(root / "state" / "hyprbar" / "settings.toml");
    out << "[theme.templates]\nenable_builtin_templates = false\n"
        << "[theme.templates.user.app-colors]\n"
        << "input_path = \"" << input.string() << "\"\n"
        << "output_path = \"" << output.string() << "\"\n";
  }
  {
    ConfigService config;
    TEST_CHECK(config.config().theme.templates.userTemplates.size() == 1);
    TemplateApplyService service(config);
    GeneratedPalette palette;
    palette.dark["surface"] = 0xff111111;
    palette.light["surface"] = 0xffeeeeee;
    std::optional<GeneratedPalette> previousPalette;
    std::optional<std::string> previousMode;
    int colorNotifications = 0;
    int modeChanges = 0;
    service.setAfterApplyCallback([&](std::string_view mode, bool colorsChanged) {
      if (colorsChanged) {
        std::ifstream in(output);
        const std::string rendered{std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>()};
        TEST_CHECK(rendered == (mode == "light" ? "#eeeeee" : "#111111"));
        ++colorNotifications;
      }
    });
    const auto resolve = [&](std::string_view mode) {
      const bool colorsChanged = noctalia::theme::appColorsChanged(previousPalette, palette, previousMode, mode);
      if (previousMode.has_value() && *previousMode != mode) {
        ++modeChanges;
      }
      previousMode = std::string(mode);
      previousPalette = palette;
      service.apply(palette, mode, /*force=*/false, /*paletteChanged=*/colorsChanged);
    };
    resolve("dark");
    settle();
    TEST_CHECK(colorNotifications == 1);
    TEST_CHECK(modeChanges == 0); // initialization is not a mode switch
    resolve("dark");
    settle();
    TEST_CHECK(colorNotifications == 1); // redundant resolution stays silent
    TEST_CHECK(modeChanges == 0);
    resolve("light");
    resolve("light"); // coalesced duplicate must preserve the owed mode-only notification
    settle();
    TEST_CHECK(colorNotifications == 2);
    TEST_CHECK(modeChanges == 1);
    resolve("dark");
    settle();
    TEST_CHECK(colorNotifications == 3);
    TEST_CHECK(modeChanges == 2);
    // A change to the non-selected half of the dual palette retains existing semantics.
    palette.light["surface"] = 0xffdddddd;
    resolve("dark");
    settle();
    TEST_CHECK(colorNotifications == 4);
    TEST_CHECK(modeChanges == 2);
  }

  ::unsetenv("HYPRBAR_CONFIG_HOME");
  ::unsetenv("HYPRBAR_STATE_HOME");
  ::unsetenv("HYPRBAR_DATA_HOME");
  std::filesystem::remove_all(root);
  return 0;
}
