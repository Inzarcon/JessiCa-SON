"""Test module for ProfileManager class and its interaction with MainSettingsManager."""

from pathlib import Path

from settings_io.main_settings_manager import MainSettingsManager
from settings_io.profile_manager import ProfileManager


def _first_start(tmp_path: str) -> tuple[MainSettingsManager, ProfileManager]:
    # Helper for simulating first startup.
    settings = MainSettingsManager(Path(tmp_path))
    profiles = ProfileManager(Path(tmp_path), settings)
    return settings, profiles


def test_first_start(tmp_path) -> None:
    """Test creation of Default Profile on first startup."""
    settings, profiles = _first_start(tmp_path)

    assert Path(tmp_path).joinpath("settings.json").is_file()
    assert Path(tmp_path).joinpath("profiles/Default.json").is_file()

    assert profiles.is_default()
    assert settings.load_setting("default_profile") == "Default"
    assert not profiles._entries


def test_default_not_found(tmp_path) -> None:
    """Test loading a default profile that does not exist."""
    settings, profiles_pre = _first_start(tmp_path)
    profiles_pre.save_setting("number", 42)
    settings.save_setting("default_profile", "Other")

    profiles = ProfileManager(tmp_path, settings)

    assert Path(tmp_path).joinpath("settings.json").is_file()
    assert Path(tmp_path).joinpath("profiles/Default.json").is_file()
    assert Path(tmp_path).joinpath("profiles/Other.json").is_file()

    assert profiles.is_default()
    assert profiles_pre.load_setting("number") == 42
    assert not profiles.load_setting("number")


def test_default_not_set_but_exists(tmp_path) -> None:
    """Test loading "Default" profile that exists, but is not set as default."""
    _, profiles_pre = _first_start(tmp_path)
    profiles_pre.save_setting("number", 42)
    settings = MainSettingsManager(Path(tmp_path))

    profiles = ProfileManager(tmp_path, settings)

    assert profiles.is_default()
    assert profiles.load_setting("number") == 42


def test_default_invalid(tmp_path) -> None:
    """Test loading a default profile that has become invalid."""
    settings, profiles_pre = _first_start(tmp_path)
    profiles_pre.save_setting("number", 42)
    with Path.open(Path(tmp_path).joinpath("profiles/Default.json"), "w") as file:
        file.write("Invalid")

    profiles = ProfileManager(tmp_path, settings)

    assert profiles.is_default()
    assert profiles._default == "Default"
    assert not profiles._entries


def test_new_and_switch(tmp_path) -> None:
    """Test creating a new profile and switching between profiles."""
    _, profiles = _first_start(tmp_path)
    profiles.save_setting("number", 42)
    profiles.create_new("New Profile")
    profiles.switch("New Profile")
    profiles.save_setting("number", 3)

    assert profiles.default_profile_name() == "Default"
    assert profiles.profile_name() == "New Profile"
    assert not profiles.is_default()
    assert profiles.load_setting("number") == 3

    profiles.switch("Default")
    assert profiles.default_profile_name() == "Default"
    assert profiles.profile_name() == "Default"
    assert profiles.is_default()
    assert profiles.load_setting("number") == 42


def test_set_default(tmp_path) -> None:
    """Test setting the a profile as new default."""
    _, profiles = _first_start(tmp_path)
    profiles.save_setting("number", 42)
    profiles.create_new("New Profile")
    profiles.switch("New Profile")
    profiles.set_as_default()
    profiles.save_setting("number", 3)

    assert profiles.default_profile_name() == "New Profile"
    assert profiles.profile_name() == "New Profile"
    assert profiles.is_default()
    assert profiles.load_setting("number") == 3

    profiles.switch("Default")
    assert profiles.default_profile_name() == "New Profile"
    assert profiles.profile_name() == "Default"
    assert not profiles.is_default()
    assert profiles.load_setting("number") == 42


def test_switch_to_default(tmp_path) -> None:
    """Test switching to the default profile."""
    _, profiles = _first_start(tmp_path)
    profiles.save_setting("number", 42)
    profiles.create_new("New Profile")

    profiles.switch_to_default()
    assert profiles.is_default()
    assert profiles.load_setting("number") == 42


def test_scan(tmp_path) -> None:
    """Test scnanning for profiles."""
    _, profiles = _first_start(tmp_path)
    profile_names = ["Default", "UltiCa", "MSX+", "Chibi Ultica", "UDP"]
    for profile_name in profile_names[1:]:
        profiles.create_new(profile_name)

    scanned = profiles.scan()
    assert len(scanned) == 5
    assert all(profile_name in scanned for profile_name in profile_names)
    assert all(profiles.profile_exists(profile_name) for profile_name in profile_names)


def test_delete(tmp_path) -> None:
    """Test deleting profiles."""
    _, profiles = _first_start(tmp_path)
    profile_names = ["Default", "UltiCa", "MSX+", "Chibi Ultica", "UDP"]
    for profile_name in profile_names[1:]:
        profiles.create_new(profile_name)

    profiles.switch("UltiCa")
    profiles.delete_profile()
    profile_names.remove("UltiCa")

    assert profiles.profile_name() == "Default"
    scanned = profiles.scan()
    assert len(scanned) == 4
    assert all(profile_name in scanned for profile_name in profile_names)
    assert all(profiles.profile_exists(profile_name) for profile_name in profile_names)


def test_delete_default(tmp_path) -> None:
    """Test trying to delete the default profile."""
    _, profiles = _first_start(tmp_path)
    profiles.create_new("New Profile")
    profiles.delete_profile()

    assert profiles.profile_name() == "Default"
    assert profiles.is_default()
    scanned = profiles.scan()
    assert len(scanned) == 2


def test_delete_old_default(tmp_path) -> None:
    """Test setting another profile as default and deleting the old default profile."""
    _, profiles = _first_start(tmp_path)
    profiles.create_new("New Profile")
    profiles.switch("New Profile")
    profiles.set_as_default()
    profiles.switch("Default")

    profiles.delete_profile()

    assert profiles.profile_name() == "New Profile"
    assert profiles.default_profile_name() == "New Profile"
    assert profiles.is_default()
    assert len(profiles.scan()) == 1
