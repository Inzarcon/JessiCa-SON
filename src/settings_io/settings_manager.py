"""Module containing SettingsManager base class."""

import json
from abc import ABC, abstractmethod
from pathlib import Path

from common.logger import get_logger

from . import SettingsObserver, SettingsObserverSavable

log = get_logger("Settings")


class SettingsManager(ABC):
    """Base class of managers for settings files such as the main settings.json and tileset profiles."""

    _dir: Path
    _file: Path

    _entries: dict[str, str | int | bool]
    _msg_file_not_found: str

    _observed_settings: dict[str, list[SettingsObserver]]

    @abstractmethod
    def __init__(self) -> None:
        """Create SettingsManager and load initial settings on application startup."""
        self._entries = {}
        self._observed_settings = {}

    def register_observer(self, observer: SettingsObserver, setting_names: list[str]) -> None:
        """Register an observer and the setting names it should be notified on."""
        for setting_name in setting_names:
            if setting_name not in self._observed_settings:
                self._observed_settings[setting_name] = [observer]
                log.info("Added observer %s to setting '%s'.", observer, setting_name)
                continue

            observers = self._observed_settings.get(setting_name)
            if observers is None:
                msg = "There are no observers for setting '%s', but it should have been added just before."
                raise ValueError(msg, setting_name)

            if observer in observers:
                log.warning("Observer %s already registered to setting '%s'. Ignoring.", observer, setting_name)
                continue

            if self._get_savable_observer(setting_name):
                log.warning(
                    "There should be only one SettingsObserverSavable instance for setting '%s'.",
                    setting_name,
                )
                continue

            self._observed_settings[setting_name].append(observer)
            log.info("Added observer %s to setting '%s'.", observer, setting_name)

    def _notify_observers(self, setting_name: str, value: str | int | bool | None) -> None:
        """Notify observers about the given setting."""
        if setting_name in self._observed_settings:
            observers = self._observed_settings.get(setting_name)
            if observers is None:
                msg = "Setting '%s' is set to be observed, but has no observers."
                raise ValueError(msg, setting_name)

            for observer in observers:
                observer.settings_notify(setting_name, value)

    def check_state(self, setting_name: str) -> None:
        """Call state of SettingsObserverSavable instances observing a setting and save."""
        self.check_states([setting_name])

    def check_states(self, setting_names: list[str]) -> None:
        """Call state of SettingsObserverSavable instances observing a setting from a given list and save."""
        if not self._observed_settings:
            log.warning("No observers registered. Ignoring.")
            return

        new_settings = {}
        for setting_name in setting_names:
            if setting_name not in self._observed_settings:
                log.warning("No observers registered for setting '%s'. Ignoring.", setting_name)
                continue

            observer = self._get_savable_observer(setting_name)
            if not observer:
                log.warning(
                    "No SettingsObserverSavable instance registered to save state from for setting '%s'. Ignoring.",
                    setting_name,
                )
                continue

            new_settings[setting_name] = observer.settings_state(setting_name)

        # Saving will cause a redundant notification back to the SettingsObserverSavable instance which just sent the
        # same state. However, this is not really a problem and the required checks would be unnecessarily complicated.
        self.save_settings(new_settings)

    def _get_savable_observer(self, setting_name: str) -> SettingsObserverSavable | None:
        """Return the SettingsObserverSavable instance registered for the given setting."""
        observers = self._observed_settings.get(setting_name)
        if observers is None:
            msg = "Setting '%s' is set to be observed, but has no observers."
            raise ValueError(msg, setting_name)
        for observer in observers:
            if isinstance(observer, SettingsObserverSavable):
                return observer
        return None

    def check_states_all(self) -> None:
        """Call state of all registered SettingsObserverSavable instances and save."""
        self.check_states(list(self._observed_settings.keys()))

    def save_setting(self, setting_name: str, value: str | int | bool) -> None:
        """Save a single setting."""
        self.save_settings({setting_name: value})

    def save_settings(self, settings: dict[str, str | int | bool]) -> None:
        """Save a dict of settings."""
        for setting_name, value in settings.items():
            if self._entries.get(setting_name) is None:
                log.info(
                    "Added new setting '%s' with value '%s' to %s.",
                    setting_name,
                    value,
                    self._file,
                )
            else:
                log.info(
                    "Overwrote setting '%s' with new value '%s' in %s.",
                    setting_name,
                    value,
                    self._file,
                )
            self._entries[setting_name] = value
            self._notify_observers(setting_name, value)

        self._entries = dict(sorted(self._entries.items()))
        self._save_json()

    def load_setting(self, setting_name: str) -> str | int | bool | None:
        """Load and return the value of a single setting."""
        result = self.load_settings([setting_name])
        return result.get(setting_name)

    def load_settings(self, setting_names: list[str]) -> dict[str, str | int | bool | None]:
        """Load and return the given settings as a dict."""
        self._load_json()  # Maybe redundant, but in case _entries and actual JSON file desynchronize for some reason.
        result = {}
        for setting_name in setting_names:
            value = self._entries.get(setting_name)
            result[setting_name] = value
            if (value) is None:
                log.warning("Setting '%s' not found in %s. Returning 'None'", setting_name, self._file)
            else:
                log.info(
                    "Loaded setting '%s' with value %s from %s.",
                    setting_name,
                    value,
                    self._file,
                )
            self._notify_observers(setting_name, value)

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
