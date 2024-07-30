"""Module containing the MainSettingsManager class."""

import sys
from json.decoder import JSONDecodeError
from pathlib import Path

from .settings_manager import SettingsManager


class MainSettingsManager(SettingsManager):
    """SettingsManager for the main settings.json file.

    Not intended to be created manually. Import the SETTINGS instance of this module instead.

    TODO: Allow user to move the settings directory. Will still need settings.json in .config to point at new directory.
          Also requires moving the files and additional checks to ensure nothing gets accidentally deleted.
    """

    _dir: Path
    _file: Path = Path("settings.json")

    _msg_file_not_found: str = "Main settings file '%s' not found; creating new. On first app startup this is normal."

    def __init__(self, directory: Path) -> None:
        """Create MainSettingsManager and load settings.json.

        If the file is invalid or does not exist (usually on first startup), a new empty config.json is created.
        """
        super().__init__()
        self._dir = directory
        try:
            self._load_json()
        except (JSONDecodeError, FileNotFoundError):
            self._dir.mkdir(exist_ok=True)
            self._save_json()


if "pytest" not in sys.modules:
    from main import CFG_PATH

    SETTINGS: MainSettingsManager = MainSettingsManager(CFG_PATH)
