from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def configured_environment() -> dict[str, str]:
    home = Path.home()
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")).expanduser()
    state_home = Path(os.environ.get("XDG_STATE_HOME", home / ".local/state")).expanduser()
    theme_dir = Path(os.environ.get(
        "HYPRBAR_BRAVE_THEME_DIR",
        home / ".local/share/hyprbar/themes/chrome",
    )).expanduser()
    user_data_dir = Path(os.environ.get(
        "HYPRBAR_BRAVE_USER_DATA_DIR",
        config_home / "BraveSoftware/Brave-Browser",
    )).expanduser()
    default_user_data_dir = Path(os.environ.get(
        "HYPRBAR_BRAVE_DEFAULT_USER_DATA_DIR",
        config_home / "BraveSoftware/Brave-Browser",
    )).expanduser()
    manifest = Path(os.environ.get(
        "HYPRBAR_BRAVE_MANIFEST", theme_dir / "manifest.json"
    )).expanduser()
    state_dir = Path(os.environ.get(
        "HYPRBAR_BRAVE_STATE_DIR", state_home / "hyprbar/brave"
    )).expanduser()

    return {
        "HYPRBAR_CHROME_USER_DATA_DIR": str(user_data_dir),
        "HYPRBAR_CHROME_DEFAULT_USER_DATA_DIR": str(default_user_data_dir),
        "HYPRBAR_CHROME_THEME_DIR": str(theme_dir),
        "HYPRBAR_CHROME_MANIFEST": str(manifest),
        "HYPRBAR_CHROME_STATE_DIR": str(state_dir),
        "HYPRBAR_CHROME_PROC_DIR": os.environ.get("HYPRBAR_BRAVE_PROC_DIR", "/proc"),
        "HYPRBAR_CHROME_BINARY": os.environ.get(
            "HYPRBAR_BRAVE_BINARY", "/opt/brave.com/brave/brave"
        ),
        "HYPRBAR_CHROME_LAUNCHER": os.environ.get(
            "HYPRBAR_BRAVE_LAUNCHER", "/usr/bin/brave-browser-stable"
        ),
        "HYPRBAR_CHROME_BROWSER_NAME": "Brave",
        "HYPRBAR_CHROME_BROWSER_SLUG": "brave",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Restart Brave when the Hyprbar theme manifest changes.")
    parser.add_argument("--dry-run", action="store_true", help="report the action without changing state or restarting Brave")
    arguments = parser.parse_args()

    core = Path(__file__).with_name("chrome-theme-restart.py")
    if not core.is_file():
        print(f"Brave theme restart core not found: {core}", file=sys.stderr)
        return 1

    environment = os.environ.copy()
    environment.update(configured_environment())
    command = [sys.executable, str(core)]
    if arguments.dry_run:
        command.append("--dry-run")
    try:
        return subprocess.run(command, env=environment, check=False).returncode
    except OSError as error:
        print(f"Could not run Brave theme restart core: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
