#include "core/files/resource_paths.h"
#include "tests/test_check.h"

#include <algorithm>
#include <array>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <string>
#include <string_view>
#include <unistd.h>

int main() {
  std::string pathTemplate = std::getenv("TMPDIR") != nullptr ? std::getenv("TMPDIR") : "/tmp";
  pathTemplate += "/hyprbar-assets-test-XXXXXX";
  char* created = ::mkdtemp(pathTemplate.data());
  TEST_CHECK(created != nullptr);
  if (created == nullptr)
    return 1;

  const std::filesystem::path root(created);
  std::filesystem::create_directories(root / "fonts");
  std::filesystem::create_directories(root / "templates");
  std::filesystem::create_directories(root / "translations");
  std::ofstream(root / "emoji.json").put(' ');
  std::ofstream(root / "hyprbar.svg").put(' ');
  std::ofstream(root / "fonts/hyprbar-tabler.ttf").put(' ');
  std::ofstream(root / "templates/builtin.toml").put(' ');
  std::ofstream(root / "translations/en.json").put(' ');
  ::setenv("HYPRBAR_ASSETS_DIR", root.c_str(), 1);
  ::setenv("NOCTALIA_ASSETS_DIR", "/tmp/noctalia-assets-must-not-be-used", 1);

  TEST_CHECK(paths::assetsRoot() == root);
  std::filesystem::remove_all(root);
  return 0;
}
