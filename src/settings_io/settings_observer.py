"""Module containing SettingsObserver and SettingsObserverSavable base classes."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from .settings_manager import SettingsManager


class SettingsObserver:
    """Interface for classes that observe settings from a SettingsManager.

    Observes settings given in the constructor and auto-updates them on changes once registered to a SettingsManager.
    Normally, this means that an instance attribute with the same name is set. If a setting name is also part of
    setting_to_func, the given function is called with the value as parameter instead.
    """

    _settings: dict[str, str | int | bool]
    _setting_to_func: dict[str, Callable] | None

    def __init__(self, settings: dict[str, str | int | bool]) -> None:
        """Create SettingsObserver. Pass dictionary with setting names as keys and default setting values as values."""
        self._settings = settings
        self._setting_to_func = None
        for setting_name, value in settings.items():
            self.settings_notify(setting_name, value)

    def set_setting_to_func(self, setting_to_func: dict[str, Callable], *, keep_attr: bool = False) -> None:
        """Set redirections of setting names to functions.

        Pass dictionary with setting names as keys and callable functions or methods as values. Keys must exist in
        settings; otherwise raises ValueError. The corresponding instance attribute created during initialization is
        also deleted unless keep_attr=True.
        """
        self._set_redirect_method(setting_to_func, name="setting_to_func", keep_attr=keep_attr)

    def _set_redirect_method(self, redirect: dict[str, Callable], name: str, *, keep_attr: bool = False) -> None:
        # Internal shortcut for set_setting_to_func and set_func_to_setting methods.
        invalid = [setting_name for setting_name in redirect if setting_name not in self._settings]
        if invalid:
            msg = f"All setting names in {name} must exist in settings, but these do not: {invalid}"
            raise ValueError(msg)

        not_callable = [func for func in redirect.values() if not callable(func)]
        if not_callable:
            msg = f"Not callable: {not_callable}"
            raise ValueError(msg)

        setattr(self, f"_{name}", redirect)
        if not keep_attr:
            for setting_name in redirect:
                if hasattr(self, setting_name):
                    delattr(self, setting_name)

    def settings_notify(self, setting_name: str, value: str | int | bool | None) -> None:
        """Notify about settings update and apply new settings. If value is None, reset back to default value."""
        if value is None:
            value = self._settings.get(setting_name)

        if self._setting_to_func and setting_name in self._setting_to_func:
            func = self._setting_to_func.get(setting_name)
            if not callable(func):
                msg = f"""Not callable: {func}. Called late in settings_notify; set_setting_to_func
                should have caught this earlier. Did you directly overwrite the attribute?"""
                raise ValueError(msg)
            func(value)

        else:
            setattr(self, setting_name, value)

    def register_at(self, settings_manager: SettingsManager) -> None:
        """Register self to a SettingsManager."""
        settings_manager.register_observer(self, list(self._settings.keys()))


class SettingsObserverSavable(SettingsObserver):
    """Interface for classes that observe settings and also have their state saved to settings files."""

    _func_to_setting: dict[str, Callable] | None

    def __init__(self, settings: dict[str, str | int | bool]) -> None:
        """Create SettingsObserverSavable. Works the same way as Parent constructor."""
        self._func_to_setting = None
        super().__init__(settings)

    def set_func_to_setting(self, func_to_setting: dict[str, Callable], *, keep_attr: bool = False) -> None:
        """Set redirections of functions to setting names.

        Works the same way as Parent.set_setting_to_func in the reverse direction.
        """
        self._set_redirect_method(func_to_setting, name="func_to_setting", keep_attr=keep_attr)

    def settings_state(self, setting_name: str) -> str | int | bool:
        """Return the current settings state of a given setting. Called by SettingsManager to update its settings."""
        if self._func_to_setting and setting_name in self._func_to_setting:
            func = self._func_to_setting.get(setting_name)
            if not callable(func):
                msg = f"""Not callable: {func}. Called late in settings_state; set_func_to_setting
                should have caught this earlier. Did you directly overwrite the attribute?"""
                raise ValueError(msg)
            return func()
        return getattr(self, setting_name)
