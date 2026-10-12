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
    r"|Noctalia v5\.2\.1"
    r"|Noctalia Greeter"
    r"|Noctalia Pywalfox native messaging host"
    r"|NoctaliaTheme"
    r"|noctalia-shell"
    r"|dev\.noctalia\.[A-Za-z0-9_.]+"
)
BRAND = re.compile(r"(?i)noctalia")
SOURCE_COMPATIBILITY_TOKENS = {
    "src/shell/bar/widgets/control_center_widget.h": BRAND,
    "src/config/cli.cpp": BRAND,
    "src/cli/schema_config.h": BRAND,
    "src/compositors/kde/kwin_active_window.cpp": BRAND,
    "src/scripting/luau_host.cpp": BRAND,
    "src/system/screen_time_service.cpp": BRAND,
    "src/theme/firefox_theme/firefox_theme.cpp": BRAND,
}
CPP_STRING = re.compile(
    r'R"(?P<delimiter>[^ ()\\]*)\((?P<raw>.*?)\)(?P=delimiter)"|"(?:\\.|[^"\\])*"',
    re.DOTALL,
)
CPP_COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.DOTALL)


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
            residual = ALLOWED_TECHNICAL_TOKENS.sub("", text)
            if BRAND.search(residual):
                errors.append(f"{source.name}:{key_path}: {text}")

    assets = root / "assets"
    for relative in (
        "freedo.svg",
        "hyprbar-wallpaper.png",
        "fonts/hyprbar-tabler.ttf",
        "licenses/GFDL-1.3.txt",
        "licenses/FREEDO-NOTICE.md",
    ):
        if not (assets / relative).is_file():
            errors.append(f"missing Hyprbar asset or license notice: {relative}")
    for relative in (
        "noctalia.svg",
        "noctalia-wallpaper.png",
        "fonts/noctalia-tabler.ttf",
    ):
        if (assets / relative).exists():
            errors.append(f"obsolete branded asset remains: {relative}")

    templates = assets / "templates"
    for source in sorted(templates.rglob("*")):
        if not source.is_file() or source.is_symlink():
            continue
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            errors.append(f"{source.relative_to(root)}: could not read shipped template: {error}")
            continue
        if BRAND.search(text):
            errors.append(f"{source.relative_to(root)}: old product branding remains in shipped theme output")

    control_center_header = (root / "src" / "shell" / "bar" / "widgets" / "control_center_widget.h").read_text(
        encoding="utf-8"
    )
    control_center_source = (root / "src" / "shell" / "bar" / "widgets" / "control_center_widget.cpp").read_text(
        encoding="utf-8"
    )
    if 'std::string customImage = defaultCustomImage();' not in control_center_header:
        errors.append("control-center custom_image must default to bundled Freedo artwork")
    if 'paths::assetPath("freedo.svg")' not in control_center_source:
        errors.append("control-center custom_image must resolve Freedo from the installed asset bundle")
    control_center_docs = root / "docs" / "user" / "bar" / "widgets" / "control-center.mdx"
    if not control_center_docs.is_file() or "bundled Freedo artwork" not in control_center_docs.read_text(encoding="utf-8"):
        errors.append("control-center docs must describe the bundled Freedo image and override")
    notice_path = assets / "licenses" / "FREEDO-NOTICE.md"
    if notice_path.is_file():
        notice = notice_path.read_text(encoding="utf-8")
        if "version 1.3" not in notice.lower() or "trademark" not in notice.lower():
            errors.append("Freedo attribution notice must record its license and trademark status")

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
        residual = ALLOWED_TECHNICAL_TOKENS.sub("", text)
        if BRAND.search(residual):
            errors.append(f"{source.relative_to(root)}: old product branding remains outside documented compatibility identifiers")

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
