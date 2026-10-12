#include "core/deferred_call.h"
#include "net/http_client.h"
#include "theme/community_templates.h"

#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <print>
#include <string>
#include <string_view>
#include <unistd.h>

namespace {
  bool check(bool condition, const char* message) {
    if (!condition) {
      std::println(stderr, "community_template_cache_compat_test: {}", message);
    }
    return condition;
  }

  bool writeFile(const std::filesystem::path& path, const std::string& contents) {
    std::filesystem::create_directories(path.parent_path());
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    if (!out) {
      return false;
    }
    out << contents;
    return out.good();
  }

  std::string readFile(const std::filesystem::path& path) {
    std::ifstream in(path, std::ios::binary);
    return {std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>()};
  }
} // namespace

int main() {
  namespace fs = std::filesystem;
  const fs::path root = fs::temp_directory_path() / ("hyprbar-community-template-cache-compat-" + std::to_string(::getpid()));
  std::error_code ec;
  fs::remove_all(root, ec);
  const fs::path cache = root / "state" / "hyprbar" / "community-templates";
  const fs::path templateDir = cache / "example";
  const fs::path templateFile = templateDir / "theme.css";
  const fs::path legacyMetadata = templateDir / ".noctalia-cache.json";
  const fs::path currentMetadata = templateDir / ".hyprbar-cache.json";

  bool ok = true;
  fs::create_directories(templateDir, ec);
  ok = check(!ec, "failed to create isolated state fixture") && ok;
  ::setenv("HYPRBAR_CONFIG_HOME", (root / "config").c_str(), 1);
  ::setenv("HYPRBAR_STATE_HOME", (root / "state").c_str(), 1);
  ::setenv("HYPRBAR_DATA_HOME", (root / "data").c_str(), 1);

  constexpr std::string_view legacyContents = "previous upstream contents";
  constexpr std::string_view legacyMd5 = "28ecde062751f6a0eacfa3b1f10556ff";
  const std::string catalog =
      R"([{"name":"example","files":[{"name":"theme.css","md5":"9c5a16d09d43994cc4f353eb1e223508"}]}])";
  const std::string metadata =
      R"({"version":1,"files":{"theme.css":"28ecde062751f6a0eacfa3b1f10556ff"}})";
  ok = check(writeFile(cache / "catalog.json", catalog), "failed to write cached catalog") && ok;
  ok = check(writeFile(templateFile, std::string(legacyContents)), "failed to write cached template") && ok;
  ok = check(writeFile(legacyMetadata, metadata), "failed to write legacy metadata") && ok;

  {
    HttpClient http;
    http.setOfflineMode(true);
    noctalia::theme::CommunityTemplateService service(http);
    ThemeConfig::TemplatesConfig config;
    config.enableCommunityTemplates = true;
    config.communityIds = {"example"};
    service.sync(config);
    for (auto& call : DeferredCall::takePending()) {
      call();
    }
  }

  const std::string migratedMetadata = readFile(currentMetadata);
  ok = check(!migratedMetadata.empty(), "Hyprbar metadata file was not written from the legacy cache") && ok;
  ok = check(migratedMetadata.find("theme.css") != std::string::npos, "legacy file entry was not preserved") && ok;
  ok = check(migratedMetadata.find(legacyMd5) != std::string::npos, "legacy file checksum was not preserved") && ok;
  ok = check(fs::exists(legacyMetadata), "legacy metadata was removed before migration was verified") && ok;
  ok = check(readFile(templateFile) == legacyContents, "cached template contents were overwritten") && ok;

  fs::remove_all(root, ec);
  return ok ? 0 : 1;
}
