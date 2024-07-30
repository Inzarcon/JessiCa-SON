"""Test module for MainSettingsManager class."""

from settings_io.main_settings_manager import MainSettingsManager


def test_first_start(tmp_path, caplog) -> None:
    """Test creation of empty settings.json when no valid one is found."""
    settings = MainSettingsManager(tmp_path)

    records = caplog.records
    assert len(records) == 1
    assert records[0].levelname == "ERROR"
    msg = records[0].getMessage()
    assert "first app startup" in msg
    assert "settings.json" in msg

    settings._load_json()  # Check if file exists now


def test_start_existing(tmp_path) -> None:
    """Test if existing settings.json is loaded during init."""
    settings_pre = MainSettingsManager(tmp_path)
    entries: dict[str, str | int | bool] = {"content": "Content", "number": 42, "include_thing": True}
    settings_pre.save_settings(entries)

    settings = MainSettingsManager(tmp_path)
    assert settings.load_settings(list(entries.keys())) == entries
