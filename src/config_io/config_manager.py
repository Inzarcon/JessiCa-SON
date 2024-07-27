"""Module containing ConfigManager base class."""

import json
from abc import ABC, abstractmethod
from pathlib import Path

from common.logger import get_logger

log = get_logger("Config")


class ConfigManager(ABC):
    """Base class of managers for configuration files such as the main settings.json and tileset profiles."""

    _dir: Path
    _file: Path

    _entries: dict[str, str | int | bool]
    _msg_file_not_found: str

    @abstractmethod
    def __init__(self) -> None:
        """Create ConfigManager and load initial settings on application startup."""
        self._entries = {}

    def save_setting(self, setting_name: str, value: str | int | bool) -> None:
        """Save a single setting."""
        self.save_settings([(setting_name, value)])

    def save_settings(self, settings: list[tuple[str, str | int | bool]]) -> None:
        """Save a list of setting tuples."""
        for setting_name, value in settings:
            if self._entries.get(setting_name) is None:
                log.info(
                    "Adding new setting %s with value %s to %s.",
                    setting_name,
                    value,
                    self._file,
                )
            else:
                log.info(
                    "Overwriting setting %s with value %s in %s.",
                    setting_name,
                    value,
                    self._file,
                )
            self._entries[setting_name] = value
        self._entries = dict(sorted(self._entries.items()))
        self._save_json()

    def load_setting(self, setting_name: str) -> str | int | bool | None:
        """Return the value of a single setting."""
        result = self.load_settings([setting_name])
        return result.get(setting_name)

    def load_settings(self, setting_names: list[str]) -> dict[str, str | int | bool | None]:
        """Return given settings as a dict."""
        self._load_json()  # Maybe redundant, but in case _entries and actual JSON file desynchronize for some reason.
        result = {}
        for setting_name in setting_names:
            result[setting_name] = self._entries.get(setting_name)
            if (value := result[setting_name]) is None:
                log.warning("Setting %s not found in %s.", setting_name, self._file)
            else:
                log.info(
                    "Loaded setting %s with value %s from %s.",
                    setting_name,
                    value,
                    self._file,
                )
        return result

    def _file_path(self) -> Path:
        return self._dir.joinpath(self._file)

    def _save_json(self) -> None:
        with Path.open(self._file_path(), "w", encoding="utf-8") as file:
            json.dump(self._entries, file, indent=4)

    def _load_json(self) -> None:
        try:
            with Path.open(self._file_path(), encoding="utf-8") as file:
                self._entries = json.load(file)
        except json.decoder.JSONDecodeError as exception:
            log.error("JSONDecodeError %s: %s", self._file_path(), exception)
            raise
        except FileNotFoundError:
            log.error(
                self._msg_file_not_found,
                self._file_path(),
            )
            raise
