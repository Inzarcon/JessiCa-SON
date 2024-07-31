"""Module containing SettingsManager base class."""

import json
from abc import ABC, abstractmethod
from pathlib import Path

from common.logger import get_logger

from . import SettingsObserver, SettingsObserverSavable

log = get_logger("Settings")


class SettingsManager(ABC):
    """Abstract base class of managers for settings files such as the main settings.json and tileset profiles.

    Handles all relevant JSON operations internally based on the _dir and _file attributes. Registers SettingsObserver
    instances and notifies them on relevant changes. In the case of SettingsObserverSavable instances, also checks their
    state and updates the settings file accordingly.
    """

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

    def load_settings(
        self, setting_names: list[str], *, allow_missing_file: bool = False
    ) -> dict[str, str | int | bool | None]:
        """Load and return the given settings as a dict.

        If allow_missing_file=True, returns None for each setting name if no valid settings file exists instead of
        raising JSONDecodeError or FileNotFoundError.
        """
        result: dict[str, str | int | bool | None]

        if allow_missing_file and not self.valid_file_exists(log_errors=False):
            result = {setting_name: None for setting_name in setting_names}
            for setting_name in result:
                self._notify_observers(setting_name, None)
            return result

        # Might seem redundant to always reload JSON file even if settings did not change, but:
        #   * self._entries and actual JSON file may desynchronize for external reasons.
        #   * JSON file may go missing or turn invalid during runtime. -> Info for debugging; higher layer can react.
        #   * Checking when or when not to reload would be more complicated to implement and test than it is worth.
        #   * Loading small JSON files is fast. (Or move to own thread if it does become a bottleneck at some point.)
        self._load_json()
        result = {}
        for setting_name in setting_names:
            value = self._entries.get(setting_name)
            result[setting_name] = value
            if (value) is None:
                log.warning("Setting '%s' not found in %s. Returning 'None'", setting_name, self._file)
            else:
                log.info(
                    "Loaded setting '%s' with value '%s' from %s.",
                    setting_name,
                    value,
                    self._file,
                )
            self._notify_observers(setting_name, value)

        return result

    def register_observer(self, observer: SettingsObserver, setting_names: list[str]) -> None:
        """Register an observer and the setting names it should be notified on.

        Usually there is no need to call this manually. The ConfigObserver instances automate passing the setting names
        via their register_at method.
        """
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
                    "There should be only one SettingsObserverSavable instance for setting '%s'. Ignoring.",
                    setting_name,
                )
                continue

            self._observed_settings[setting_name].append(observer)
            log.info("Added observer %s to setting '%s'.", observer, setting_name)
        self.load_settings(setting_names, allow_missing_file=True)

    def check_state(self, setting_name: str, *, auto_save: bool = True) -> None:
        """Call state of SettingsObserverSavable instance observing a setting and save. Shortcut to check_states()."""
        self.check_states([setting_name], auto_save=auto_save)

    def check_states(self, setting_names: list[str], *, auto_save: bool = True) -> None:
        """Call state of SettingsObserverSavable instances observing a setting from the given list and save.

        If auto_save=False, the ProfileManager still updates its internal setting entries, but does not save them to the
        current profile JSON file. Mainly used when creating a new profile.
        """
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

            new_settings[setting_name] = observer.setting_state(setting_name)

        if auto_save:
            # Saving will cause redundant notifications back to the SettingsObserverSavables instances which just sent
            # their same state. However, this is usually not a problem and checking which specific observers to notify
            # would be unnecessarily complicated, similar to always loading the JSON file in load_settings().
            self.save_settings(new_settings)
        else:
            self._entries.update(new_settings)

    def check_states_all(self, *, auto_save: bool = True) -> None:
        """Check states of all registered SettingsObserverSavable instances and save. Shortcut to check_states()."""
        setting_names = [
            setting_name for setting_name in self._observed_settings if self._get_savable_observer(setting_name)
        ]
        self.check_states(setting_names, auto_save=auto_save)

    def valid_file_exists(self, *, other_file: Path | None = None, log_errors: bool = True) -> bool:
        """Return whether the current settings file (or other_file if passed) exists and contains valid JSON.

        If log_errors=False, no JSONDecodeError or FileNotFoundError will be logged. Used for pure checks where such
        messages would be redundant. Examples are registering observers and loading their then empty settings during the
        first startup, or the ProfileManager subclass which has its own context-specific messages when profiles do not
        exist.
        """
        other_file = other_file if other_file else self._file
        try:
            self._load_json(check_only=True, log_errors=log_errors, other_file=other_file)
            return True
        except (json.decoder.JSONDecodeError, FileNotFoundError):
            return False

    def _file_path(self, *, other_file: Path | None = None) -> Path:
        file = other_file if other_file else self._file
        return self._dir.joinpath(file)

    def _save_json(self, *, empty_file: bool = False, other_file: Path | None = None) -> None:
        with Path.open(self._file_path(other_file=other_file), "w", encoding="utf-8") as file:
            entries = {} if empty_file else self._entries
            json.dump(entries, file, indent=4)

    def _load_json(self, *, check_only: bool = False, log_errors: bool = True, other_file: Path | None = None) -> None:
        try:
            with Path.open(self._file_path(other_file=other_file), encoding="utf-8") as file:
                if check_only:
                    json.load(file)
                else:
                    self._entries = json.load(file)
        except json.decoder.JSONDecodeError as exception:
            if log_errors:
                log.error("JSONDecodeError %s: %s", self._file_path(other_file=other_file), exception)
            raise
        except FileNotFoundError:
            if log_errors:
                log.error(self._msg_file_not_found, self._file_path(other_file=other_file))
            raise

    def _notify_observers(self, setting_name: str, value: str | int | bool | None) -> None:
        if setting_name in self._observed_settings:
            observers = self._observed_settings.get(setting_name)
            if observers is None:
                msg = "Setting '%s' is set to be observed, but has no observers."
                raise ValueError(msg, setting_name)

            for observer in observers:
                observer.setting_update(setting_name, value)

    def _notify_observers_all(self) -> None:
        for setting_name in self._observed_settings:
            self._notify_observers(setting_name, self.load_setting(setting_name))

    def _get_savable_observer(self, setting_name: str) -> SettingsObserverSavable | None:
        # Assumes that there is one savable instance as register_observer should ensure.
        observers = self._observed_settings.get(setting_name)
        if observers is None:
            msg = "Setting '%s' is set to be observed, but has no observers."
            raise ValueError(msg, setting_name)
        for observer in observers:
            if isinstance(observer, SettingsObserverSavable):
                return observer
        return None
