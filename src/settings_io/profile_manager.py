"""Module containing the ProfileManager class."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from common.logger import get_logger

from .settings_manager import SettingsManager

log = get_logger("Profiles")

if TYPE_CHECKING:
    from logging import Logger


class ProfileManager(SettingsManager):
    """SettingsManager for profile JSON files.

    Not intended to be created manually. Import the PROFILES instance of this module instead.
    """

    _dir: Path
    _file: Path

    _msg_file_not_found: str = "Profile '%s' not found."

    _settings_mgr: SettingsManager
    _default: str

    def __init__(self, directory: Path, settings_mgr: SettingsManager, *, log: Logger = log) -> None:
        """Create ProfileManager."""
        super().__init__(log=log)
        self._dir = directory.joinpath("profiles")
        self._settings_mgr = settings_mgr

        default = settings_mgr.load_setting("default_profile")
        if type(default) is str:
            self.set_as_default(other_profile=default, auto_save=False)
        else:
            self._log.error("No valid default profile name set; using 'Default'. On first app startup this is normal.")
            default = "Default"
            self.set_as_default(other_profile=default)
        self.switch(default)

    def create_new(self, new_profile: str, *, force_overwrite: bool = False, empty_file: bool = True) -> None:
        """Create a new profile if does not already exist or force_overwrite=True.

        If empty_file=False, the current state is be saved to the new profile. The current profile is not changed
        either way.
        """
        if self.profile_exists(new_profile):
            if force_overwrite:
                self._log.warning("Overwriting existing profile '%s' with new profile.", new_profile)
            else:
                self._log.warning("Profile '%s' already exists. Ignoring.", new_profile)
                return

        self._dir.mkdir(exist_ok=True)
        self.check_states_all(auto_save=False)
        self._save_json(empty_file=empty_file, other_file=self._profile_to_file(new_profile))
        self._log.info("Created new profile '%s'", new_profile)

    def switch(self, profile: str) -> None:
        """Switch to another profile and notify observers."""
        is_default = self.is_default(other_profile=profile)
        if not self.profile_exists(profile):
            if is_default:
                self._log.error(
                    "Default profile '%s' not found or invalid; creating new. On first app startup this is normal."
                )
                self.create_new(profile, force_overwrite=True)
            else:
                self._log.warning("Profile '%s' not found. Ignoring.", profile)
                return
        self._file = self._profile_to_file(profile)

        profile_type = "default" if is_default else ""
        self._log.info("Switched to %s profile '%s'.", profile_type, profile)
        self._notify_observers_all()

    def switch_to_default(self) -> None:
        """Switch to default profile."""
        if self.is_default():
            self._log.warning("Profile '%s' already is the default profile.", self.profile_name)
            return
        self.switch(self._default)

    def is_default(self, *, other_profile: str | None = None) -> bool:
        """Return whether the currently loaded profile (or other_profile if passed) is the default profile."""
        profile = other_profile if other_profile else self.profile_name()
        return self._default == profile

    def set_as_default(self, *, other_profile: str | None = None, auto_save: bool = True) -> None:
        """Set current profile (or other profile if passed) as new default.

        If auto_save=False, "default_profile" in settings.json is not updated. Mainly used by __init__ to
        avoid redundant overwrite and log message during startup.
        """
        profile = other_profile if other_profile else self.profile_name()
        self._default = profile
        if auto_save:
            self._settings_mgr.save_setting("default_profile", profile)

    def profile_name(self) -> str:
        """Return name of the current profile."""
        return self._file.stem

    def default_profile_name(self) -> str:
        """Return name of the default profile."""
        return self._default

    def profile_exists(self, profile_name: str) -> bool:
        """Return whether a profile with the given name exists."""
        return self.valid_file_exists(other_file=self._profile_to_file(profile_name), log_errors=False)

    def scan(self) -> list[str]:
        """Return list of valid profiles found in the profile directory."""
        result = [file.stem for file in list(self._dir.iterdir()) if file.is_file() and file.suffix == ".json"]
        self._log.info("Scanned for profiles. Found: %s", result)
        return result

    def delete_profile(self, *, other_profile: str | None = None) -> None:
        """Delete a profile unless it is the default profile."""
        profile = other_profile if other_profile else self.profile_name()
        if not self.profile_exists(profile):
            self._log.warning("Profile '%s' does not exist. Nothing to delete.", profile)
            return
        if self.is_default(other_profile=profile):
            self._log.warning("Profile '%s' is the default profile. Not deleting.", profile)
            return

        self._file_path(other_file=self._profile_to_file(profile)).unlink()
        self._log.info("Deleted profile '%s'.", profile)
        if not other_profile:
            self.switch_to_default()

    @staticmethod
    def _profile_to_file(profile: str) -> Path:
        return Path(f"{profile}.json")

    def _set_profile(self, profile: str) -> None:
        self._file = self._profile_to_file(profile)


if "pytest" not in sys.modules:
    from main import CFG_PATH

    from . import SETTINGS

    PROFILES: ProfileManager = ProfileManager(CFG_PATH, SETTINGS)
