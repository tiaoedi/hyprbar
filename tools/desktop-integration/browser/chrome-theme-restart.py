from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import signal
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Paths:
    user_data_dir: Path
    default_user_data_dir: Path
    theme_dir: Path
    manifest: Path
    state_dir: Path
    proc_dir: Path
    chrome_binary: Path
    chrome_launcher: Path
    browser_name: str
    browser_slug: str


def configured_paths() -> Paths:
    home = Path.home()
    state_home = Path(os.environ.get("XDG_STATE_HOME", home / ".local/state"))
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")).expanduser()
    theme_dir = Path(os.environ.get(
        "HYPRBAR_CHROME_THEME_DIR",
        home / ".local/share/hyprbar/themes/chrome",
    )).expanduser()
    browser_slug = Path(os.environ.get("HYPRBAR_CHROME_BROWSER_SLUG", "chrome")).name
    if browser_slug in {"", ".", ".."}:
        browser_slug = "chrome"
    return Paths(
        user_data_dir=Path(os.environ.get(
            "HYPRBAR_CHROME_USER_DATA_DIR", config_home / "google-chrome"
        )).expanduser(),
        default_user_data_dir=Path(os.environ.get(
            "HYPRBAR_CHROME_DEFAULT_USER_DATA_DIR", config_home / "google-chrome"
        )).expanduser(),
        theme_dir=theme_dir,
        manifest=Path(os.environ.get(
            "HYPRBAR_CHROME_MANIFEST", theme_dir / "manifest.json"
        )).expanduser(),
        state_dir=Path(os.environ.get(
            "HYPRBAR_CHROME_STATE_DIR", state_home / "hyprbar"
        )).expanduser(),
        proc_dir=Path(os.environ.get("HYPRBAR_CHROME_PROC_DIR", "/proc")),
        chrome_binary=Path(os.environ.get(
            "HYPRBAR_CHROME_BINARY", "/opt/google/chrome/chrome"
        )).expanduser(),
        chrome_launcher=Path(os.environ.get(
            "HYPRBAR_CHROME_LAUNCHER", "/usr/bin/google-chrome-stable"
        )).expanduser(),
        browser_name=os.environ.get("HYPRBAR_CHROME_BROWSER_NAME", "Chrome"),
        browser_slug=browser_slug,
    )


def manifest_digest(manifest: Path) -> str:
    return hashlib.sha256(manifest.read_bytes()).hexdigest()


def active_theme_profiles(user_data_dir: Path, theme_dir: Path) -> tuple[str, list[str]]:
    """Return the browser's last-used profile and profiles actively using this theme."""
    try:
        local_state: dict[str, Any] = json.loads((user_data_dir / "Local State").read_text())
    except (OSError, json.JSONDecodeError, TypeError):
        return "Default", []

    profile_info = local_state.get("profile", {})
    if not isinstance(profile_info, dict):
        return "Default", []
    last_used = profile_info.get("last_used", "Default")
    if not isinstance(last_used, str) or not last_used or Path(last_used).name != last_used or last_used in {".", ".."}:
        last_used = "Default"

    info_cache = profile_info.get("info_cache", {})
    profile_names = set(info_cache) if isinstance(info_cache, dict) else set()
    profile_names.update({"Default", last_used})
    expected_path = theme_dir.resolve(strict=False)
    active_profiles: list[str] = []

    for profile in sorted(profile_names):
        if not isinstance(profile, str) or not profile or Path(profile).name != profile or profile in {".", ".."}:
            continue
        try:
            preferences: dict[str, Any] = json.loads(
                (user_data_dir / profile / "Preferences").read_text()
            )
        except (OSError, json.JSONDecodeError, TypeError):
            continue

        extensions = preferences.get("extensions", {})
        if not isinstance(extensions, dict):
            continue
        settings = extensions.get("settings", {})
        theme = extensions.get("theme", {})
        active_id = theme.get("id") if isinstance(theme, dict) else None
        if not isinstance(settings, dict):
            continue

        for extension_id, setting in settings.items():
            if not isinstance(setting, dict) or not isinstance(setting.get("path"), str):
                continue
            extension_path = Path(setting["path"]).expanduser().resolve(strict=False)
            if extension_path == expected_path and not setting.get("disable_reasons") and extension_id == active_id:
                active_profiles.append(profile)
                break

    return last_used, active_profiles


def _argument_value(arguments: list[str], name: str) -> str | None:
    prefix = f"{name}="
    for index, argument in enumerate(arguments):
        if argument.startswith(prefix):
            return argument[len(prefix):]
        if argument == name and index + 1 < len(arguments):
            return arguments[index + 1]
    return None


def chrome_main_pids(
    proc_dir: Path,
    chrome_binary: Path,
    user_data_dir: Path,
    default_user_data_dir: Path | None = None,
) -> list[int]:
    """Find only matching Chromium browser processes using this user-data directory."""
    expected_executable = chrome_binary.resolve(strict=False)
    expected_data_dir = user_data_dir.resolve(strict=False)
    pids: list[int] = []
    try:
        entries = list(proc_dir.iterdir())
    except OSError:
        return pids

    for entry in entries:
        if not entry.name.isdecimal():
            continue
        try:
            executable = (entry / "exe").resolve(strict=False)
            if executable != expected_executable:
                continue
            raw_arguments = (entry / "cmdline").read_bytes()
            arguments = [part.decode(errors="replace") for part in raw_arguments.split(b"\0") if part]
            if len(arguments) == 1 and " " in arguments[0]:
                arguments = shlex.split(arguments[0])
            if not arguments or "--type" in arguments or any(
                argument.startswith("--type=") for argument in arguments
            ):
                continue
            explicit_data_dir = _argument_value(arguments, "--user-data-dir")
            if explicit_data_dir:
                if Path(explicit_data_dir).expanduser().resolve(strict=False) != expected_data_dir:
                    continue
            else:
                if default_user_data_dir is None:
                    xdg_config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
                    default_user_data_dir = xdg_config / "google-chrome"
                default_data_dir = default_user_data_dir.resolve(strict=False)
                if expected_data_dir != default_data_dir:
                    continue
            pids.append(int(entry.name))
        except (OSError, ValueError, ProcessLookupError):
            continue
    return sorted(pids)


def _write_state(state_file: Path, digest: str) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    temporary = state_file.with_name(f".{state_file.name}.{os.getpid()}.tmp")
    temporary.write_text(f"{digest}\n")
    os.replace(temporary, state_file)


def _log(state_dir: Path, message: str) -> None:
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        browser_slug = Path(os.environ.get("HYPRBAR_CHROME_BROWSER_SLUG", "chrome")).name
        if browser_slug in {"", ".", ".."}:
            browser_slug = "chrome"
        with (state_dir / f"{browser_slug}-theme-restart.log").open("a") as log_file:
            log_file.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} {message}\n")
    except OSError:
        print(message, file=sys.stderr)


def _emit(dry_run: bool, action: str, **details: Any) -> None:
    if dry_run:
        print(json.dumps({"action": action, **details}, sort_keys=True))


def _wait_until_stopped(paths: Paths, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not chrome_main_pids(
            paths.proc_dir,
            paths.chrome_binary,
            paths.user_data_dir,
            paths.default_user_data_dir,
        ):
            return True
        time.sleep(0.25)
    return False


def _invalidate_theme_cache(paths: Paths) -> bool:
    # Chromium can reuse this compiled package without comparing it to the
    # unpacked theme's manifest. Only call after shutdown (or while closed).
    try:
        (paths.theme_dir / "Cached Theme.pak").unlink(missing_ok=True)
    except OSError as error:
        _log(paths.state_dir, f"Cannot invalidate {paths.browser_name} theme cache: {error}")
        return False
    return True


def _restart(paths: Paths, profile: str, pids: list[int]) -> bool:
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            continue
        except OSError as error:
            _log(paths.state_dir, f"Could not request {paths.browser_name} shutdown for pid {pid}: {error}")
            return False

    if not _wait_until_stopped(paths):
        _log(paths.state_dir, f"{paths.browser_name} did not exit cleanly within 15 seconds; restart aborted")
        return False

    if not _invalidate_theme_cache(paths):
        return False

    command = [
        str(paths.chrome_launcher),
        "--ozone-platform=x11",
        f"--profile-directory={profile}",
        "--restore-last-session",
    ]
    if paths.user_data_dir.resolve(strict=False) != paths.default_user_data_dir.resolve(strict=False):
        command.append(f"--user-data-dir={paths.user_data_dir}")
    environment = os.environ.copy()
    environment.setdefault("GTK_IM_MODULE", "cedilla")
    try:
        subprocess.Popen(
            command,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    except OSError as error:
        _log(paths.state_dir, f"{paths.browser_name} relaunch failed: {error}")
        return False

    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        if chrome_main_pids(
            paths.proc_dir,
            paths.chrome_binary,
            paths.user_data_dir,
            paths.default_user_data_dir,
        ):
            return True
        time.sleep(0.25)
    _log(paths.state_dir, f"{paths.browser_name} relaunch was requested but no browser process appeared within 15 seconds")
    return False


def run(dry_run: bool = False) -> int:
    paths = configured_paths()
    state_file = paths.state_dir / f"{paths.browser_slug}-theme-restart.sha256"
    lock_file = paths.state_dir / f"{paths.browser_slug}-theme-restart.lock"

    try:
        digest = manifest_digest(paths.manifest)
    except OSError as error:
        _log(paths.state_dir, f"Theme manifest unavailable; no restart: {error}")
        _emit(dry_run, "manifest_unavailable")
        return 0

    paths.state_dir.mkdir(parents=True, exist_ok=True)
    try:
        lock_handle = lock_file.open("a")
    except OSError as error:
        _log(paths.state_dir, f"Cannot open restart lock; no restart: {error}")
        _emit(dry_run, "lock_unavailable")
        return 0

    with lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)

        try:
            previous = state_file.read_text().strip()
        except FileNotFoundError:
            previous = ""
        except OSError as error:
            _log(paths.state_dir, f"Cannot read restart state; no restart: {error}")
            _emit(dry_run, "state_unavailable")
            return 0

        if not previous:
            if not dry_run:
                _write_state(state_file, digest)
                _log(paths.state_dir, f"Initialized current {paths.browser_name} theme baseline; no restart")
            _emit(dry_run, "baseline")
            return 0
        if previous == digest:
            _emit(dry_run, "unchanged")
            return 0

        profile, active_profiles = active_theme_profiles(paths.user_data_dir, paths.theme_dir)
        if not active_profiles:
            if not dry_run:
                _write_state(state_file, digest)
                _log(paths.state_dir, f"Skipped: Hyprbar theme extension is not active in any {paths.browser_name} profile")
            _emit(dry_run, "theme_not_active", profile=profile)
            return 0

        pids = chrome_main_pids(
            paths.proc_dir,
            paths.chrome_binary,
            paths.user_data_dir,
            paths.default_user_data_dir,
        )
        if not pids:
            if not dry_run:
                if not _invalidate_theme_cache(paths):
                    return 1
                _write_state(state_file, digest)
                _log(paths.state_dir, f"{paths.browser_name} is closed; theme cache invalidated for its next start")
            _emit(dry_run, f"{paths.browser_slug}_not_running", profile=profile, active_profiles=active_profiles)
            return 0

        if dry_run:
            _emit(dry_run, "would_restart", profile=profile, active_profiles=active_profiles, pid=pids[0])
            return 0

        _log(paths.state_dir, f"Palette changed; restarting {paths.browser_name} profile {profile}; theme active in {', '.join(active_profiles)}")
        if not _restart(paths, profile, pids):
            _emit(dry_run, "restart_failed", profile=profile, active_profiles=active_profiles)
            return 1
        _write_state(state_file, digest)
        _log(paths.state_dir, f"{paths.browser_name} restarted for profile {profile}; theme active in {', '.join(active_profiles)}")
        _emit(dry_run, "restarted", profile=profile, active_profiles=active_profiles)
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report the action without changing state or restarting Chrome")
    arguments = parser.parse_args()
    return run(dry_run=arguments.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
