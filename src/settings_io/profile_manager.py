"""Module containing the ProfileManager class."""

import sys
from json.decoder import JSONDecodeError
from pathlib import Path

from common.logger import get_logger

from .settings_manager import SettingsManager

log = get_logger("Profiles")


class ProfileManager(SettingsManager):
    """SettingsManager for profile JSON files.

    Not intended to be created manually. Import the PROFILES instance of this module instead.
    """

    _dir: Path
    _file: Path

    _msg_file_not_found: str = "Profile '%s' not found."

    _settings_mgr: SettingsManager
    _default: str

    def __init__(self, directory: Path, settings_mgr: SettingsManager) -> None:
        """Create ProfileManager."""
        super().__init__()
        self._dir = directory.joinpath("profiles")
        self._settings_mgr = settings_mgr

        default = settings_mgr.load_setting("default_profile")
        if type(default) is str:
            self.set_as_default(other_profile=default, skip_save=True)
        else:
            log.error("No valid default profile name set; using 'Default'. On first app startup this is normal.")
            default = "Default"
            self.set_as_default(other_profile=default)

        if not self.profile_exists(default):
            self.create_new(default, skip_check=True)
        self.switch(default)

    def create_new(self, new_profile: str, *, overwrite: bool = False, skip_check: bool = False) -> None:
        """Create a new profile if does not already exist or overwrite=True.

        If skip_check=True, file will be created without checking for existing file at all. Mainly used by __init__ to
        avoid redundant check and log message after already determining that the file does not exist.
        """
        if not skip_check and self.profile_exists(new_profile):
            if overwrite:
                log.warning("Overwriting existing profile '%s' with new empty profile.", new_profile)
            else:
                log.warning("Profile '%s' already exists. Ignoring.", new_profile)
                return

        self._dir.mkdir(exist_ok=True)
        self._save_json(create_only=True, other_file=self._profile_to_file(new_profile))
        log.info("Created new profile '%s'", new_profile)

    def switch(self, profile: str) -> None:
        """Switch to another profile and notify observers."""
        if not self.profile_exists(profile):
            if self.is_default(other_profile=profile):
                log.error("Default profile '%s' not found or invalid. Creating new.")
                self.create_new(profile, overwrite=True)
            else:
                log.warning("Profile '%s' not found. Ignoring.", profile)
                return
        self._file = self._profile_to_file(profile)
        log.info("Switched to profile '%s'.", profile)
        self._notify_observers_all()

    def switch_to_default(self) -> None:
        """Switch to default profile."""
        if self.is_default():
            log.warning("Profile '%s' already is the default profile.", self.profile_name)
            return
        self.switch(self._default)

    def is_default(self, *, other_profile: str | None = None) -> bool:
        """Return whether the currently loaded profile (or other_profile if passed) is the default profile."""
        profile = other_profile if other_profile else self.profile_name()
        return self._default == profile

    def set_as_default(self, *, other_profile: str | None = None, skip_save: bool = False) -> None:
        """Set current profile (or other profile if passed) as new default.

        If skip_save=True, "default_profile" in settings.json is not updated. Mainly used by __init__ to
        avoid redundant overwrite and log message during startup.
        """
        profile = other_profile if other_profile else self.profile_name()
        self._default = profile
        if not skip_save:
            self._settings_mgr.save_setting("default_profile", profile)

    def profile_name(self) -> str:
        """Return name of the current profile."""
        return self._file.stem

    def default_profile_name(self) -> str:
        """Return name of the default profile."""
        return self._default

    def profile_exists(self, profile_name: str) -> bool:
        """Return whether a profile with the given name exists."""
        try:
            self._load_json(check_only=True, other_file=self._profile_to_file(profile_name))
            return True
        except (JSONDecodeError, FileNotFoundError):
            return False

    def scan(self) -> list[str]:
        """Return list of valid profiles found in the profile directory."""
        files = list(self._dir.iterdir())
        return [file.stem for file in files if file.is_file() and file.suffix == ".json"]

    def delete_profile(self, *, other_profile: str | None = None) -> None:
        """Delete a profile unless it is the default profile."""
        profile = other_profile if other_profile else self.profile_name()
        if not self.profile_exists(profile):
            log.warning("Profile '%s' does not exist. Nothing to delete.")
            return
        if self.is_default(other_profile=profile):
            log.warning("Profile '%s' is the default profile. Not deleting.")
            return

        self._file_path(other_file=self._profile_to_file(profile)).unlink()
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
