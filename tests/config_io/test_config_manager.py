"""Test module for ConfigManager base class."""

from json import JSONDecodeError
from pathlib import Path

import pytest
from config_io.config_manager import ConfigManager


class _BaseConfigManager(ConfigManager):
    _msg_file_not_found: str = "File %s not found."

    def __init__(self, tmp_path: Path) -> None:
        super().__init__()
        self._dir = tmp_path
        self._file = Path("test_settings.json")


class TestJSON:
    """Tests for JSON IO."""

    @staticmethod
    def test_single(tmp_path, caplog) -> None:
        """Test saving and loading single setting."""
        cfg = _BaseConfigManager(tmp_path)
        cfg.save_setting("test_setting", "test_value")
        assert cfg.load_setting("test_setting") == "test_value"

        records = caplog.records
        assert len(records) == 2

        assert records[0].levelname == "INFO"
        msg0 = records[0].getMessage()
        assert msg0.startswith("Adding")
        assert "test_setting" in msg0
        assert "test_value" in msg0

        assert records[1].levelname == "INFO"
        msg1 = records[1].getMessage()
        assert msg1.startswith("Loaded")
        assert "test_setting" in msg1
        assert "test_value" in msg1

    @staticmethod
    def test_multiple(tmp_path) -> None:
        """Test saving and loading multiple settings."""
        cfg = _BaseConfigManager(tmp_path)
        cfg.save_settings(
            [
                ("test_setting", "test_value"),
                ("test_str", "some string"),
                ("test_int", 42),
                ("test_bool", True),
            ]
        )
        assert cfg.load_setting("test_setting") == "test_value"
        assert cfg.load_setting("test_str") == "some string"
        assert cfg.load_setting("test_int") == 42
        assert cfg.load_setting("test_bool")

        settings_loaded = cfg.load_settings(["test_str", "test_int", "test_bool"])

        assert len(settings_loaded) == 3
        assert settings_loaded.get("test_setting") is None
        assert settings_loaded.get("test_str") == "some string"
        assert settings_loaded.get("test_int") == 42
        assert settings_loaded.get("test_bool")

    @staticmethod
    def test_overwrite(tmp_path, caplog) -> None:
        """Test overwriting setting."""
        cfg = _BaseConfigManager(tmp_path)
        cfg.save_setting("test_setting", "test_value")
        cfg.save_setting("test_setting", "overwritten")
        assert cfg.load_setting("test_setting") == "overwritten"

        records = caplog.records
        assert len(records) == 3

        assert records[1].levelname == "INFO"
        msg = records[1].getMessage()
        assert msg.startswith("Overwriting")
        assert "test_setting" in msg
        assert "overwritten" in msg

    @staticmethod
    def test_load_setting_not_exist(tmp_path, caplog) -> None:
        """Test loading setting that does not exist."""
        cfg = _BaseConfigManager(tmp_path)
        cfg.save_setting("test_setting", "test_value")
        assert cfg.load_setting("test_setting_not_exist") is None

        records = caplog.records
        assert len(records) == 2
        assert records[1].levelname == "WARNING"
        msg = records[1].getMessage()
        assert "not found" in msg
        assert "test_setting_not_exist" in msg
        assert "test_settings.json" in msg

    @staticmethod
    def test_load_file_not_exist(tmp_path, caplog) -> None:
        """Test loading file that does not exist."""
        cfg = _BaseConfigManager(tmp_path)
        with pytest.raises(FileNotFoundError) as _:
            cfg.load_setting("test_setting")

        records = caplog.records
        assert len(records) == 1
        assert records[0].levelname == "ERROR"
        assert "test_settings.json not found." in records[0].getMessage()

    @staticmethod
    def test_load_file_invalid_json(tmp_path, caplog) -> None:
        """Test loading file containing invalid json."""
        cfg = _BaseConfigManager(tmp_path)
        cfg.save_setting("test_setting", "test_value")
        with Path.open(tmp_path.joinpath("test_settings.json"), "w") as file:
            file.write("invalid")
        with pytest.raises(JSONDecodeError) as _:
            cfg.load_setting("test_setting")

        records = caplog.records
        assert len(records) == 2
        assert records[1].levelname == "ERROR"
        msg = records[1].getMessage()
        assert "JSONDecodeError" in msg
        assert "test_settings.json" in msg

        # Check if loaded entries intact.
        assert len(cfg._entries) == 1
        assert cfg._entries.get("test_setting") == "test_value"
