#pragma once

#include <array>
#include <string_view>

namespace settings::about {

  inline constexpr std::string_view productName = "Hyprbar";
  inline constexpr std::string_view developer = "sebastao .o santana";

  struct Link {
    std::string_view labelKey;
    std::string_view url;
    std::string_view glyph;
  };

  inline constexpr std::array<Link, 3> links{{
      {"settings.about.developer-profile", "https://github.com/tiaoedi", "brand-github"},
      {"settings.about.project", "https://github.com/tiaoedi/hyprbar", "external-link"},
      {"settings.about.youtube", "https://www.youtube.com/@linuxlivre9008", "brand-youtube"},
  }};

} // namespace settings::about
