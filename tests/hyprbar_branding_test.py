#!/usr/bin/env python3
"""Guard user-facing translations and shipped identity assets against regressions."""

from __future__ import annotations

import json
import re
import struct
import sys
from pathlib import Path
from typing import Any


ALLOWED_TECHNICAL_TOKENS = re.compile(
    r"(?i)noctalia-(?:dock|osd)"
    r"|noctalia-greeter(?:-[a-z0-9_-]+)?"
    r"|noctalia-glyph:[a-z0-9_-]*"
    r"|noctalia/[a-z0-9_./-]+"
    r"|noctalia-dev/[a-z0-9_./-]+"
    r"|noctalia\.[a-z0-9_.]+"
    r"|NOCTALIA_[A-Z0-9_]+"
    r"|noctalia:[a-z0-9_-]+"
    r"|noctalia\.(?:dev|cachix\.org)(?:/[a-z0-9_./?=&%-]*)?"
    r"|noctalia\.(?:css|toml|log)"
    r"|import-noctalia"
    r"|NoctaliaTheme"
    r"|noctalia-shell"
    r"|dev\.noctalia\.[A-Za-z0-9_.]+"
)
BRAND = re.compile(r"(?i)noctalia")
# Known provider/endpoint attributions are unsupported by the inspected client path.
LOCATION_SOURCE_CLAIM = re.compile(
    r"(?i)the plugin catalog|(?:api\.)?noctalia\.dev|https?://|プラグインカタログ"
)
SOURCE_COMPATIBILITY_TOKENS = {
    "src/shell/bar/widgets/control_center_widget.h": BRAND,
    "src/config/cli.cpp": BRAND,
    "src/cli/schema_config.h": BRAND,
    "src/compositors/kde/kwin_active_window.cpp": BRAND,
    "src/scripting/luau_host.cpp": BRAND,
    "src/system/screen_time_service.cpp": BRAND,
    "src/theme/firefox_theme/firefox_theme.cpp": BRAND,
}
# Exact legacy literals remain recognized where removing them could break upgrades or external integrations.
PERSISTENT_COMPATIBILITY_LITERALS = {
    "src/security/secret_store.cpp": {"noctalia"},
    "src/theme/community_templates.cpp": {".noctalia-cache.json"},
    "src/theme/firefox_theme/manifest.cpp": {"Noctalia Pywalfox native messaging host"},
}
# The GTK helper recognizes the previous import only to rewrite it to Hyprbar's CSS file.
TEMPLATE_COMPATIBILITY_REPLACEMENTS = {
    "gtk/apply.sh": ("(noctalia|hyprbar)", "(hyprbar)"),
}
CPP_STRING = re.compile(
    r'R"(?P<delimiter>[^ ()\\]*)\((?P<raw>.*?)\)(?P=delimiter)"|"(?:\\.|[^"\\])*"',
    re.DOTALL,
)
CPP_COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.DOTALL)


FORK_ORIGIN_DESCRIPTIONS = {
    "README.md": "Fork independente baseado no código-fonte do **Noctalia v5.2.1**:",
    "CREDITS.md": "Hyprbar is an independent fork based on the Noctalia v5.2.1 source project",
}


def documentation_prose(text: str) -> str:
    visible: list[str] = []
    in_fence = False
    fence_marker = ""
    for line in text.splitlines():
        stripped = line.lstrip()
        marker = "```" if stripped.startswith("```") else "~~~" if stripped.startswith("~~~") else ""
        if marker:
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = ""
            continue
        if in_fence:
            continue
        parts = line.split("`")
        line = "".join(parts[::2])
        while "](" in line:
            start = line.find("](")
            end = line.find(")", start + 2)
            if end < 0:
                break
            line = line[: start + 1] + line[end + 1 :]
        for scheme in ("https://", "http://"):
            while scheme in line:
                start = line.find(scheme)
                end = start
                while end < len(line) and not line[end].isspace() and line[end] not in ")>]:":
                    end += 1
                line = line[:start] + line[end:]
        while "<" in line and ">" in line:
            start = line.find("<")
            end = line.find(">", start + 1)
            if end < 0:
                break
            line = line[:start] + line[end + 1 :]
        visible.append(line)
    return "\n".join(visible)


def strings(value: Any, path: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            found.extend(strings(child, f"{path}.{key}" if path else str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(strings(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        found.append((path, value))
    return found


def cpp_string_literals(text: str) -> list[tuple[str, int]]:
    literals: list[tuple[str, int]] = []
    index = 0
    while index < len(text):
        if text.startswith("//", index):
            newline = text.find(chr(10), index)
            index = len(text) if newline < 0 else newline + 1
        elif text.startswith("/*", index):
            end = text.find("*/", index + 2)
            index = len(text) if end < 0 else end + 2
        elif text.startswith('R"', index):
            opening = text.find("(", index + 2)
            if opening < 0:
                break
            delimiter = text[index + 2 : opening]
            closing = ")" + delimiter + '"'
            end = text.find(closing, opening + 1)
            if end < 0:
                break
            literals.append((text[opening + 1 : end], index))
            index = end + len(closing)
        elif text[index] == '"':
            start = index + 1
            index = start
            while index < len(text):
                if ord(text[index]) == 92:
                    index += 2
                elif text[index] == '"':
                    literals.append((text[start:index], start - 1))
                    index += 1
                    break
                else:
                    index += 1
        elif text[index] == "'":
            index += 1
            while index < len(text):
                if ord(text[index]) == 92:
                    index += 2
                elif text[index] == "'":
                    index += 1
                    break
                else:
                    index += 1
        else:
            index += 1
    return literals


def font_name_strings(path: Path) -> list[str]:
    data = path.read_bytes()
    table_count = struct.unpack_from(">H", data, 4)[0]
    name_offset = name_length = None
    for index in range(table_count):
        record_offset = 12 + index * 16
        tag = data[record_offset : record_offset + 4]
        offset, length = struct.unpack_from(">II", data, record_offset + 8)
        if tag == b"name":
            name_offset, name_length = offset, length
            break
    if name_offset is None or name_length is None:
        raise ValueError("font has no OpenType name table")
    _, count, storage_offset = struct.unpack_from(">HHH", data, name_offset)
    strings: list[str] = []
    for index in range(count):
        record_offset = name_offset + 6 + index * 12
        platform, _, _, _, length, offset = struct.unpack_from(">HHHHHH", data, record_offset)
        start = name_offset + storage_offset + offset
        raw = data[start : start + length]
        encoding = "utf-16-be" if platform in (0, 3) else "mac_roman" if platform == 1 else "latin-1"
        strings.append(raw.decode(encoding, errors="replace"))
    return strings


def main(root: Path) -> int:
    errors: list[str] = []
    translations = root / "assets" / "translations"
    for source in sorted(translations.glob("*.json")):
        try:
            document = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{source.name}: invalid translation JSON: {error}")
            continue
        for key_path, text in strings(document):
            if key_path.endswith(".location-auto-locate.description"):
                if "ip" not in text.casefold():
                    errors.append(f"{source.name}:{key_path}: location description must identify IP-based detection")
                if LOCATION_SOURCE_CLAIM.search(text):
                    errors.append(f"{source.name}:{key_path}: location description contains an unsupported provider or endpoint claim")
            residual = ALLOWED_TECHNICAL_TOKENS.sub("", text)
            if BRAND.search(residual):
                errors.append(f"{source.name}:{key_path}: {text}")

    assets = root / "assets"
    for relative in (
        "hyprbar.svg",
        "hyprbar-wallpaper.svg",
        "hyprbar-wallpaper.png",
        "fonts/hyprbar-tabler.ttf",
    ):
        if not (assets / relative).is_file():
            errors.append(f"missing Hyprbar asset: {relative}")
    for relative in (
        "noctalia.svg",
        "noctalia-wallpaper.png",
        "fonts/noctalia-tabler.ttf",
        "freedo.svg",
        "licenses/GFDL-1.3.txt",
        "licenses/FREEDO-NOTICE.md",
    ):
        if (assets / relative).exists():
            errors.append(f"excluded upstream artwork or obsolete branded asset remains: {relative}")

    templates = assets / "templates"
    for source in sorted(templates.rglob("*")):
        if not source.is_file() or source.is_symlink():
            continue
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            errors.append(f"{source.relative_to(root)}: could not read shipped template: {error}")
            continue
        compatibility = TEMPLATE_COMPATIBILITY_REPLACEMENTS.get(source.relative_to(templates).as_posix())
        if compatibility is not None:
            legacy_match, hyprbar_match = compatibility
            if legacy_match not in text:
                errors.append(f"{source.relative_to(root)}: legacy GTK import migration matcher is missing")
            text = text.replace(legacy_match, hyprbar_match, 1)
        if BRAND.search(text):
            errors.append(f"{source.relative_to(root)}: old product branding remains in shipped theme output")

    control_center_header = (root / "src" / "shell" / "bar" / "widgets" / "control_center_widget.h").read_text(
        encoding="utf-8"
    )
    control_center_source = (root / "src" / "shell" / "bar" / "widgets" / "control_center_widget.cpp").read_text(
        encoding="utf-8"
    )
    if 'std::string customImage = defaultCustomImage();' not in control_center_header:
        errors.append("control-center custom_image must retain its configured default")
    if 'paths::assetPath("hyprbar.svg")' not in control_center_source:
        errors.append("control-center custom_image must resolve the Hyprbar icon from the installed asset bundle")
    control_center_docs = root / "docs" / "user" / "bar" / "widgets" / "control-center.mdx"
    if not control_center_docs.is_file() or "The bundled Hyprbar icon is used by default." not in control_center_docs.read_text(encoding="utf-8"):
        errors.append("control-center docs must describe the bundled Hyprbar icon and override")

    unwanted_artwork = re.compile(r"(?i)freedo|gnu linux-libre|fsfla|gfdl-1\.3")
    for relative in ("hyprbar.svg", "hyprbar-wallpaper.svg"):
        path = assets / relative
        if path.is_file() and unwanted_artwork.search(path.read_text(encoding="utf-8")):
            errors.append(f"{relative}: excluded mascot artwork/provenance remains")
    public_docs = list(root.glob("*.md")) + list(root.glob("*.mdx"))
    for documentation_root in (root / "docs",):
        public_docs.extend(documentation_root.rglob("*.md"))
        public_docs.extend(documentation_root.rglob("*.mdx"))
    public_docs.extend((root / "packaging/rpm/README.md", root / "example.toml"))
    public_docs = sorted(set(public_docs))
    for source in public_docs:
        if not source.is_file():
            continue
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            errors.append(f"{source.relative_to(root)}: could not read public documentation: {error}")
            continue
        if unwanted_artwork.search(text):
            errors.append(f"{source.relative_to(root)}: excluded mascot artwork/provenance remains in public docs")
        allowed_origin = FORK_ORIGIN_DESCRIPTIONS.get(source.relative_to(root).as_posix())
        if allowed_origin is not None:
            if text.count(allowed_origin) != 1:
                errors.append(f"{source.relative_to(root)}: expected exactly one fork-origin description")
            text = text.replace(allowed_origin, " ", 1)
        prose = documentation_prose(text)
        residual = ALLOWED_TECHNICAL_TOKENS.sub("", prose)
        if BRAND.search(residual):
            errors.append(f"{source.relative_to(root)}: old product branding remains outside the fork-origin description")

    font_path = assets / "fonts" / "hyprbar-tabler.ttf"
    if font_path.is_file():
        try:
            names = font_name_strings(font_path)
            for name in names:
                if BRAND.search(name):
                    errors.append(f"embedded font name retains upstream branding: {name}")
        except (OSError, ValueError, struct.error) as error:
            errors.append(f"could not inspect font name table: {error}")

    docs = root / "docs" / "user"
    for source in sorted(docs.rglob("*.mdx")):
        try:
            text = source.read_text(encoding="utf-8")
        except OSError as error:
            errors.append(f"{source.relative_to(root)}: could not read documentation: {error}")
            continue
        residual = ALLOWED_TECHNICAL_TOKENS.sub("", documentation_prose(text))
        if BRAND.search(residual):
            errors.append(f"{source.relative_to(root)}: old product branding remains outside technical identifiers and code examples")

    source_root = root / "src"
    for source in sorted(source_root.rglob("*")):
        if source.suffix not in {".cpp", ".h", ".hpp"}:
            continue
        relative = str(source.relative_to(root))
        if relative.startswith("src/shell/test/"):
            continue
        try:
            text = source.read_text(encoding="utf-8")
        except OSError as error:
            errors.append(f"{source.relative_to(root)}: could not read source: {error}")
            continue
        for literal, offset in cpp_string_literals(text):
            if literal in PERSISTENT_COMPATIBILITY_LITERALS.get(relative, set()):
                continue
            residual = ALLOWED_TECHNICAL_TOKENS.sub("", literal)
            if compatibility_tokens := SOURCE_COMPATIBILITY_TOKENS.get(relative):
                residual = compatibility_tokens.sub("", residual)
            if BRAND.search(residual):
                line = text.count(chr(10), 0, offset) + 1
                errors.append(f"{source.relative_to(root)}:{line}: old product branding in string literal: {literal[:100]}")

    if errors:
        print(f"Hyprbar branding check failed ({len(errors)} finding(s)):", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1
    print("Hyprbar branding check passed")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: hyprbar_branding_test.py SOURCE_ROOT")
    raise SystemExit(main(Path(sys.argv[1])))
