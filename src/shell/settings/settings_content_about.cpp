#include "shell/settings/settings_content_about.h"

#include "core/build_info.h"
#include "core/files/resource_paths.h"
#include "i18n/i18n.h"
#include "net/url_open.h"
#include "shell/settings/settings_about_metadata.h"
#include "ui/builders.h"
#include "ui/palette.h"
#include "ui/style.h"

#include <cmath>
#include <string>
#include <utility>

namespace settings {

  void addSettingsAbout(Flex& content, const SettingsAboutContext& ctx) {
    const float scale = ctx.uiScale;
    auto section = ui::column({
        .align = FlexAlign::Stretch,
        .gap = Style::spaceMd * scale,
        .padding = Style::spaceLg * scale,
        .fillWidth = true,
    });
    auto title = ui::row(
        {.align = FlexAlign::Center, .gap = Style::spaceSm * scale, .fillWidth = true},
        ui::glyph({
            .glyph = "info-circle",
            .glyphSize = Style::fontSizeHeader * scale,
            .color = colorSpecFromRole(ColorRole::Primary),
        }),
        ui::label({
            .text = i18n::tr("settings.navigation.sections.about"),
            .fontSize = Style::fontSizeHeader * scale,
            .fontWeight = FontWeight::Bold,
            .color = colorSpecFromRole(ColorRole::Primary),
        })
    );
    if (ctx.pageTitleRow != nullptr && ctx.pageTitleRow->children().empty()) {
      ctx.pageTitleRow->addChild(std::move(title));
    } else {
      section->addChild(std::move(title));
    }

    constexpr float logoSize = 128.0F;
    auto logo = ui::image({.fit = ImageFit::Contain, .width = logoSize * scale, .height = logoSize * scale});
    // Decode at the output's pixel scale, independently of the logical UI size.
    (void)logo->setSourceFile(
        ctx.renderer, paths::assetPath("hyprbar.svg").string(),
        static_cast<int>(std::ceil(logoSize * ctx.contentScale)), true
    );
    section->addChild(ui::row({.justify = FlexJustify::Center}, std::move(logo)));
    section->addChild(ui::label({
        .text = std::string(about::productName),
        .fontSize = Style::fontSizeHeader * scale,
        .fontWeight = FontWeight::Bold,
        .color = colorSpecFromRole(ColorRole::OnSurface),
    }));
    section->addChild(ui::label({
        .text = i18n::tr("settings.about.version", "version", noctalia::build_info::displayVersion()),
        .fontSize = Style::fontSizeBody * scale,
        .color = colorSpecFromRole(ColorRole::OnSurfaceVariant),
    }));
    section->addChild(ui::label({
        .text = i18n::tr("settings.about.developer", "name", std::string(about::developer)),
        .fontSize = Style::fontSizeBody * scale,
        .color = colorSpecFromRole(ColorRole::OnSurface),
    }));
    for (const auto& link : about::links) {
      section->addChild(ui::button({
          .text = i18n::tr(link.labelKey),
          .glyph = std::string(link.glyph),
          .fontSize = Style::fontSizeBody * scale,
          .glyphSize = Style::fontSizeBody * scale,
          .variant = ButtonVariant::Ghost,
          .tooltip = std::string(link.url),
          .minHeight = Style::controlHeightSm * scale,
          .paddingV = Style::spaceXs * scale,
          .paddingH = Style::spaceSm * scale,
          .radius = Style::scaledRadiusSm(scale),
          .onClick = [url = std::string(link.url)]() { (void)net::openInBrowser(url); },
      }));
    }
    section->addChild(ui::label({
        .text = i18n::tr("settings.about.provenance"),
        .fontSize = Style::fontSizeBody * scale,
        .color = colorSpecFromRole(ColorRole::OnSurfaceVariant),
        .maxLines = 0,
    }));
    section->addChild(ui::label({
        .text = i18n::tr("settings.about.license"),
        .fontSize = Style::fontSizeCaption * scale,
        .color = colorSpecFromRole(ColorRole::OnSurfaceVariant),
        .maxLines = 0,
    }));
    content.addChild(std::move(section));
  }

} // namespace settings
