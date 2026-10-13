#include "shell/settings/settings_registry.h"
#include "tests/test_check.h"

#include <algorithm>

int main() {
  using settings::SettingsSection;
  const auto descriptors = settings::settingsSectionDescriptors();
  const auto about =
      std::ranges::find(descriptors, SettingsSection::About, &settings::SettingsSectionDescriptor::section);
  TEST_CHECK(about != descriptors.end());
  TEST_CHECK(about->id == "about");
  TEST_CHECK(about->glyph == "info-circle");
  TEST_CHECK(about->sidebar);
  TEST_CHECK(about->alwaysShow);
  TEST_CHECK(settings::settingsSectionFromId("about") == SettingsSection::About);
  TEST_CHECK(settings::settingsSectionId(SettingsSection::About) == "about");
  TEST_CHECK(settings::settingsSectionLabelKey(SettingsSection::About) == "settings.navigation.sections.about");
  TEST_CHECK(settings::sectionGlyph(SettingsSection::About) == "info-circle");
  return 0;
}
