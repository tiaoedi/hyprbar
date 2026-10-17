#pragma once

#include "theme/palette.h"

#include <optional>
#include <string>
#include <string_view>

namespace noctalia::theme {

  // Whether app-facing colors_changed consumers need a notification after templates apply.
  [[nodiscard]] inline bool appColorsChanged(
      const std::optional<GeneratedPalette>& previousPalette, const GeneratedPalette& palette,
      const std::optional<std::string>& previousMode, std::string_view mode
  ) {
    return !previousPalette.has_value() || *previousPalette != palette
        || (previousMode.has_value() && *previousMode != mode);
  }

} // namespace noctalia::theme
