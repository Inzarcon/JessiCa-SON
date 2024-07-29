"""Module containing SettingsObserver and SettingsObserverSavable base classes."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from .settings_manager import SettingsManager


class SettingsObserver:
    """Interface for classes that observe settings from a SettingsManager.

    Observes settings given in the constructor and auto-updates them on changes once registered to a SettingsManager.
    Normally, this means that an instance attribute with the same name is set. If a setting name was also passed to
    set_settings_to_callables, the given callable is used instead of overwriting the respective instance attribute
    directly. This is primarily useful for binding setting names to setters of Qt Widget states such as
    QCheckBox.setChecked.

    The subclass SettingsObserverSavable also has a set_callables_to_settings method and works in both directions.
    """

    _settings: dict[str, str | int | bool]
    _settings_to_callables: dict[str, Callable] | None

    def __init__(
        self,
        settings: dict[str, str | int | bool],
    ) -> None:
        """Create SettingsObserver. Pass dictionary with setting names as keys and default setting values as values."""
        self._settings = settings
        self._settings_to_callables = None
        for setting_name, value in settings.items():
            self.setting_update(setting_name, value)

    def set_settings_to_callables(self, settings_to_callables: dict[str, Callable], *, keep_attr: bool = False) -> None:
        """Set setting_update method to use given callables instead of overwriting the instance attributes directly.

        Pass dictionary with setting names as keys and Callables as values. Keys must exist in
        settings; otherwise raises ValueError. The corresponding instance attribute created and named after the setting
        during initialization is also deleted unless keep_attr=True.

        Also calls setting_update once for each affected setting in order to apply its default value after the
        redirection.
        """
        self._set_redirect_method(settings_to_callables, name="settings_to_callables", keep_attr=keep_attr)
        for setting_name in settings_to_callables:
            self.setting_update(setting_name, None)

    def _set_redirect_method(self, redirections: dict[str, Callable], name: str, *, keep_attr: bool = False) -> None:
        # Internal shortcut for set_settings_to_callables and set_callables_to_settings methods.
        invalid = [setting_name for setting_name in redirections if setting_name not in self._settings]
        if invalid:
            msg = f"All setting names in {name} must exist in settings, but these do not: {invalid}"
            raise ValueError(msg)

        not_callable = [func for func in redirections.values() if not callable(func)]
        if not_callable:
            msg = f"Not callable: {not_callable}"
            raise ValueError(msg)

        setattr(self, f"_{name}", redirections)
        if not keep_attr:
            for setting_name in redirections:
                if hasattr(self, setting_name):
                    delattr(self, setting_name)

    def setting_update(self, setting_name: str, value: str | int | bool | None) -> None:
        """Notify about setting update and apply new setting. If value is None, reset back to default value."""
        if value is None:
            value = self._settings.get(setting_name)

        if self._settings_to_callables and setting_name in self._settings_to_callables:
            func = self._settings_to_callables.get(setting_name)
            if not callable(func):
                msg = (
                    f"Not callable: {func}. Found late in setting_update; set_settings_to_callables"
                    "should have caught this earlier. Did you directly overwrite the _settings_to_callables attribute?"
                )
                raise ValueError(msg)
            func(value)

        else:
            setattr(self, setting_name, value)

    def register_at(self, settings_manager: SettingsManager) -> None:
        """Register self to a SettingsManager."""
        settings_manager.register_observer(self, list(self._settings.keys()))


class SettingsObserverSavable(SettingsObserver):
    """Interface for classes that observe settings and also have their state saved to settings files.

    Works the same way as the base SettingsObserver for observing settings and auto-updating on changes.

    If a setting name was also passed to set_callables_to_settings, the given callable is used instead of reading from
    the respective instance attribute directly. This is like set_settings_to_callables in the reverse direction, binding
    setting names to getters of the observer's state such as QCheckBox.isChecked. The current state can then be saved
    by the SettingsManager.
    """

    _callables_to_settings: dict[str, Callable] | None

    def __init__(self, settings: dict[str, str | int | bool]) -> None:
        """Create SettingsObserverSavable. Works the same way as the base constructor."""
        super().__init__(settings)
        self._callables_to_settings = None

    def set_callables_to_settings(self, callables_to_settings: dict[str, Callable], *, keep_attr: bool = False) -> None:
        """Set settings_state method to use given callables instead of reading from an instance attribute directly.

        Works the same way as base SettingsObserver.set_settings_to_callables in the reverse direction.
        """
        self._set_redirect_method(callables_to_settings, name="callables_to_settings", keep_attr=keep_attr)

    def settings_state(self, setting_name: str) -> str | int | bool:
        """Return the current settings state of a given setting. Called by SettingsManager to update its settings."""
        if self._callables_to_settings and setting_name in self._callables_to_settings:
            func = self._callables_to_settings.get(setting_name)
            if not callable(func):
                msg = (
                    f"Not callable: {func}. Found late in settings_state; set_callables_to_settings"
                    "should have caught this earlier. Did you directly overwrite the _callables_to_settings attribute?"
                )
                raise ValueError(msg)
            return func()
        return getattr(self, setting_name)
