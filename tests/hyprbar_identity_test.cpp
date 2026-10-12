#include "util/file_utils.h"
#include "tests/test_check.h"

#include <cstdlib>
#include <string>

namespace {
  void set(const char* key, const std::string& value) {
    TEST_CHECK(::setenv(key, value.c_str(), 1) == 0);
  }

  void unset(const char* key) {
    TEST_CHECK(::unsetenv(key) == 0);
  }
} // namespace

int main() {
  constexpr const char* home = "/tmp/hyprbar-identity-home";
  set("HOME", home);
  set("XDG_CONFIG_HOME", "/tmp/hyprbar-identity-xdg/config");
  set("XDG_STATE_HOME", "/tmp/hyprbar-identity-xdg/state");
  set("XDG_DATA_HOME", "/tmp/hyprbar-identity-xdg/data");
  set("NOCTALIA_CONFIG_HOME", "/tmp/noctalia-must-not-be-used/config");
  set("NOCTALIA_STATE_HOME", "/tmp/noctalia-must-not-be-used/state");
  set("NOCTALIA_DATA_HOME", "/tmp/noctalia-must-not-be-used/data");
  unset("HYPRBAR_CONFIG_HOME");
  unset("HYPRBAR_STATE_HOME");
  unset("HYPRBAR_DATA_HOME");

  TEST_CHECK(FileUtils::configDir() == "/tmp/hyprbar-identity-xdg/config/hyprbar");
  TEST_CHECK(FileUtils::stateDir() == "/tmp/hyprbar-identity-xdg/state/hyprbar");
  TEST_CHECK(FileUtils::dataDir() == "/tmp/hyprbar-identity-xdg/data/hyprbar");

  set("HYPRBAR_CONFIG_HOME", "/tmp/hyprbar-identity-custom/config-root");
  set("HYPRBAR_STATE_HOME", "/tmp/hyprbar-identity-custom/state-root");
  set("HYPRBAR_DATA_HOME", "/tmp/hyprbar-identity-custom/data-root");
  TEST_CHECK(FileUtils::configDir() == "/tmp/hyprbar-identity-custom/config-root/hyprbar");
  TEST_CHECK(FileUtils::stateDir() == "/tmp/hyprbar-identity-custom/state-root/hyprbar");
  TEST_CHECK(FileUtils::dataDir() == "/tmp/hyprbar-identity-custom/data-root/hyprbar");

  unset("HYPRBAR_CONFIG_HOME");
  unset("HYPRBAR_STATE_HOME");
  unset("HYPRBAR_DATA_HOME");
  unset("XDG_CONFIG_HOME");
  unset("XDG_STATE_HOME");
  unset("XDG_DATA_HOME");
  TEST_CHECK(FileUtils::configDir() == std::string(home) + "/.config/hyprbar");
  TEST_CHECK(FileUtils::stateDir() == std::string(home) + "/.local/state/hyprbar");
  TEST_CHECK(FileUtils::dataDir() == std::string(home) + "/.local/share/hyprbar");

  return 0;
}
