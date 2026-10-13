#pragma once

class Flex;
class Renderer;

namespace settings {

  struct SettingsAboutContext {
    Renderer& renderer;
    // Output buffer scale multiplied by accessibility UI scale, for image decoding.
    float contentScale = 1.0F;
    float uiScale = 1.0F;
    Flex* pageTitleRow = nullptr;
  };

  // Fully custom, read-only About page; owns all link callbacks in its UI subtree.
  void addSettingsAbout(Flex& content, const SettingsAboutContext& ctx);

} // namespace settings
