"""Test module for ProfileSelector widget and its interaction with the ProfileManager and SettingsObservers."""

from pathlib import Path

from settings_io import SettingsObserver, SettingsObserverSavable
from settings_io.main_settings_manager import MainSettingsManager
from settings_io.profile_manager import ProfileManager
from settings_io.widgets import ProfileSelector


class _Observer(SettingsObserver):
    content: str


class _ObserverSavable(SettingsObserverSavable):
    savable_content: str


def _setup(
    tmp_path: str, qtbot
) -> tuple[MainSettingsManager, ProfileManager, ProfileSelector, _Observer, _ObserverSavable]:
    # Shortcut for setting up managers, ProfileSelector and some observers like when starting the app.
    settings = MainSettingsManager(Path(tmp_path))
    profiles = ProfileManager(Path(tmp_path), settings)
    selector = ProfileSelector(profiles)
    qtbot.addWidget(selector)
    obs = _Observer({"content": "Initial Content"})
    obs.register_at(profiles)
    obs_sv = _ObserverSavable({"savable_content": "Initial Savable Content"})
    obs_sv.register_at(profiles)

    return settings, profiles, selector, obs, obs_sv


def _setup_preset(tmp_path: str) -> None:
    # Shortcut for creating a few profiles before starting test.
    settings = MainSettingsManager(Path(tmp_path))
    profiles = ProfileManager(Path(tmp_path), settings)

    profiles.save_settings({"content": "Default Content", "savable_content": "Default Savable Content"})

    profiles.create_new("Second Profile")
    profiles.switch("Second Profile")
    profiles.save_settings({"content": "Second Content", "savable_content": "Second Savable Content"})

    profiles.create_new("Another Profile")
    profiles.switch("Another Profile")
    profiles.save_settings({"content": "Another Content", "savable_content": "Another Savable Content"})


def test_first_start(tmp_path, qtbot) -> None:
    """Test state of ProfileSelector after first start."""
    _, _, selector, obs, obs_sv = _setup(tmp_path, qtbot)

    assert selector.edit_profile_name.text() == "Default"
    assert selector.btn_save.text() == "Overwrite Profile"
    assert selector.combo.currentText() == "Default"
    assert selector.combo.currentIndex() == 0
    assert selector.combo.count() == 1
    assert selector._entries() == ["Default"]
    assert not selector.btn_set_as_default.isEnabled()
    assert not selector.btn_delete.isEnabled()

    assert obs.content == "Initial Content"
    assert obs_sv.savable_content == "Initial Savable Content"


def test_start_existing_profiles(tmp_path, qtbot) -> None:
    """Test state of ProfileSelector after start when there are existing profiles."""
    _setup_preset(tmp_path)
    _, _, selector, obs, obs_sv = _setup(tmp_path, qtbot)

    assert selector.edit_profile_name.text() == "Default"
    assert selector.btn_save.text() == "Overwrite Profile"
    assert selector.combo.currentText() == "Default"
    assert selector.combo.count() == 3

    assert selector.combo.currentIndex() == 1
    assert selector._entries() == ["Another Profile", "Default", "Second Profile"]

    assert obs.content == "Default Content"
    assert obs_sv.savable_content == "Default Savable Content"


def test_switch(tmp_path, qtbot) -> None:
    """Test switching profile."""
    _setup_preset(tmp_path)
    _, profile, selector, obs, obs_sv = _setup(tmp_path, qtbot)

    selector.combo.setCurrentText("Second Profile")
    assert profile.profile_name() == "Second Profile"
    assert selector.combo.currentText() == "Second Profile"
    assert selector.combo.count() == 3
    assert selector.combo.currentIndex() == 2
    assert selector.btn_set_as_default.isEnabled()
    assert selector.btn_delete.isEnabled()

    assert obs.content == "Second Content"
    assert obs_sv.savable_content == "Second Savable Content"


def test_overwrite(tmp_path, qtbot) -> None:
    """Test overwriting the current profile with changed settings."""
    _setup_preset(tmp_path)
    _, _, selector, _, obs_sv = _setup(tmp_path, qtbot)

    obs_sv.savable_content = "Overwritten Content"
    selector.btn_save.click()

    selector.combo.setCurrentText("Second Profile")
    assert obs_sv.savable_content == "Second Savable Content"
    selector.combo.setCurrentText("Default")
    assert obs_sv.savable_content == "Overwritten Content"


def test_create_new(tmp_path, qtbot) -> None:
    """Test creating a new profile with the current settings."""
    _setup_preset(tmp_path)
    _, profiles, selector, _, obs_sv = _setup(tmp_path, qtbot)

    obs_sv.savable_content = "New Savable Content"
    selector.edit_profile_name.setText("New Profile")
    assert selector.btn_save.text() == "Create new Profile"
    selector.btn_save.click()

    assert selector.combo.currentText() == "New Profile"
    assert profiles.profile_name() == "New Profile"
    assert obs_sv.savable_content == "New Savable Content"
    assert selector.combo.count() == 4
    assert selector.combo.currentIndex() == 2
    assert selector._entries() == ["Another Profile", "Default", "New Profile", "Second Profile"]

    selector.combo.setCurrentText("Default")
    assert obs_sv.savable_content == "Default Savable Content"

    selector.combo.setCurrentText("New Profile")
    assert obs_sv.savable_content == "New Savable Content"


def test_delete(tmp_path, qtbot) -> None:
    """Test deleting the current profile."""
    _setup_preset(tmp_path)
    _, profiles, selector, _, _ = _setup(tmp_path, qtbot)

    selector.combo.setCurrentText("Another Profile")
    selector.delete_profile()

    assert profiles.profile_name() == "Default"
    assert not profiles.profile_exists("Another Profile")
    assert selector.combo.currentText() == "Default"
    assert selector.edit_profile_name.text() == "Default"
    assert selector.combo.count() == 2
