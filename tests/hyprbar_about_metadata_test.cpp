#include "shell/settings/settings_about_metadata.h"
#include "tests/test_check.h"

int main() {
  namespace about = settings::about;
  TEST_CHECK(about::productName == "Hyprbar");
  TEST_CHECK(about::developer == "sebastao .o santana");
  TEST_CHECK(about::links.size() == 3);
  TEST_CHECK(about::links[0].url == "https://github.com/tiaoedi");
  TEST_CHECK(about::links[1].url == "https://github.com/tiaoedi/hyprbar");
  TEST_CHECK(about::links[2].url == "https://www.youtube.com/@linuxlivre9008");
  TEST_CHECK(about::links[0].labelKey == "settings.about.developer-profile");
  TEST_CHECK(about::links[1].labelKey == "settings.about.project");
  TEST_CHECK(about::links[2].labelKey == "settings.about.youtube");
  return 0;
}
