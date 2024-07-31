"""Test module for SettingsManager and SettingsObserver base classes. Combined since they work closely together."""

from json import JSONDecodeError
from pathlib import Path

import pytest
from PySide6.QtWidgets import QCheckBox
from settings_io import SettingsObserver, SettingsObserverSavable
from settings_io.settings_manager import SettingsManager


# Simple implementations for testing base class functionality.
class _BaseSettingsManager(SettingsManager):
    _file = Path("test_settings.json")
    _msg_file_not_found: str = "File %s not found."

    def __init__(self, tmp_path: Path) -> None:
        super().__init__()
        self._dir = tmp_path


class _BaseSettingsObserver(SettingsObserver):
    content: str
    other: str
    number: int
    include_thing: bool

    def other_method(self, value: str) -> None:
        """Set other_setting value. For testing redirection of setting to Callable."""
        self.other_setting = value


class _BaseSettingsObserverSavable(SettingsObserverSavable):
    content: str
    number: int
    include_thing: bool

    def set_other(self, value: str) -> None:
        """Set other_setting value. For testing redirection of setting to Callable."""
        self.other_setting = value

    def get_other(self) -> str:
        """Get other_setting value. For testing redirection of Callable to setting."""
        return self.other_setting


class TestJSON:
    """Tests for pure JSON IO without SettingsObserver."""

    @staticmethod
    def test_single(tmp_path, caplog) -> None:
        """Test saving and loading single setting."""
        cfg = _BaseSettingsManager(tmp_path)
        cfg.save_setting("test_setting", "test_value")
        assert cfg.load_setting("test_setting") == "test_value"

        records = caplog.records
        assert len(records) == 2

        assert records[0].levelname == "INFO"
        msg0 = records[0].getMessage()
        assert msg0.startswith("Added")
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
        cfg = _BaseSettingsManager(tmp_path)
        cfg.save_settings(
            {
                "test_setting": "test_value",
                "test_str": "some string",
                "test_int": 42,
                "test_bool": True,
            }
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
        cfg = _BaseSettingsManager(tmp_path)
        cfg.save_setting("test_setting", "test_value")
        cfg.save_setting("test_setting", "overwritten")
        assert cfg.load_setting("test_setting") == "overwritten"

        records = caplog.records
        assert len(records) == 3

        assert records[1].levelname == "INFO"
        msg = records[1].getMessage()
        assert msg.startswith("Overwrote")
        assert "test_setting" in msg
        assert "overwritten" in msg

    @staticmethod
    def test_load_setting_not_exist(tmp_path, caplog) -> None:
        """Test loading setting that does not exist."""
        cfg = _BaseSettingsManager(tmp_path)
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
        cfg = _BaseSettingsManager(tmp_path)
        with pytest.raises(FileNotFoundError) as _:
            cfg.load_setting("test_setting")

        records = caplog.records
        assert len(records) == 1
        assert records[0].levelname == "ERROR"
        assert "test_settings.json not found." in records[0].getMessage()

    @staticmethod
    def test_load_file_invalid_json(tmp_path, caplog) -> None:
        """Test loading file containing invalid json."""
        cfg = _BaseSettingsManager(tmp_path)
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


class TestSettingsObserver:
    """Tests for interaction between SettingsManager and SettingsObserver."""

    @staticmethod
    def test_register(tmp_path, caplog) -> None:
        """Test registering SettingsObserver to SettingsManager."""
        obs = _BaseSettingsObserver({"content": "Initial State"})
        cfg = _BaseSettingsManager(tmp_path)
        obs.register_at(cfg)

        records = caplog.records
        assert len(records) == 1

        assert records[0].levelname == "INFO"
        msg = records[0].getMessage()
        assert msg.startswith("Added")
        assert "_BaseSettingsObserver" in msg
        assert "content" in msg

    @staticmethod
    def test_register_twice(tmp_path, caplog) -> None:
        """Test registering SettingsObserver to SettingsManager with the same setting twice."""
        obs = _BaseSettingsObserver({"content": "Initial State"})
        cfg = _BaseSettingsManager(tmp_path)
        obs.register_at(cfg)
        obs.register_at(cfg)

        records = caplog.records
        assert len(records) == 2

        assert records[1].levelname == "WARNING"
        msg = records[1].getMessage()
        assert "already registered" in msg
        assert "_BaseSettingsObserver" in msg
        assert "content" in msg

    @staticmethod
    def test_single_setting(tmp_path) -> None:
        """Test saving and loading single setting."""
        obs = _BaseSettingsObserver({"content": "Initial State"})
        assert obs.content == "Initial State"

        cfg = _BaseSettingsManager(tmp_path)
        obs.register_at(cfg)

        cfg.save_setting("content", "New State")
        assert obs.content == "New State"

        cfg.save_setting("unrelated", "Unrelated")
        assert obs.content == "New State"

    @staticmethod
    def test_multiple_settings(tmp_path) -> None:
        """Test saving and loading multiple settings."""
        obs = _BaseSettingsObserver({"content": "Initial State", "number": 42, "include_thing": True})
        assert obs.content == "Initial State"
        assert obs.number == 42
        assert obs.include_thing

        cfg = _BaseSettingsManager(tmp_path)
        obs.register_at(cfg)

        cfg.save_settings({"content": "New State", "number": 2, "include_thing": False, "unrelated": "Unrelated"})
        assert obs.content == "New State"
        assert obs.number == 2
        assert not obs.include_thing

    @staticmethod
    def test_multiple_observers_different_settings(tmp_path) -> None:
        """Test multiple observers with different settings."""
        cfg = _BaseSettingsManager(tmp_path)
        obs1 = _BaseSettingsObserver({"content": "Initial State"})
        obs1.register_at(cfg)
        obs2 = _BaseSettingsObserver({"number": 42})
        obs2.register_at(cfg)

        cfg.save_settings({"content": "New State", "number": 2, "unrelated": "Unrelated"})

        assert obs1.content == "New State"
        assert obs2.number == 2

    @staticmethod
    def test_multiple_observers_same_settings(tmp_path) -> None:
        """Test multiple observers with the same setting."""
        cfg = _BaseSettingsManager(tmp_path)
        obs1 = _BaseSettingsObserver({"content": "Initial State"})
        obs1.register_at(cfg)
        obs2 = _BaseSettingsObserver({"content": "Initial State"})
        obs2.register_at(cfg)

        cfg.save_settings({"content": "New State", "unrelated": "Unrelated"})

        assert obs1.content == "New State"
        assert obs2.content == "New State"

    @staticmethod
    def test_settings_to_callables(tmp_path) -> None:
        """Test redirecting a setting to a Callable."""
        cfg = _BaseSettingsManager(tmp_path)
        obs = _BaseSettingsObserver({"content": "Initial State", "other": "Other Inital State"})
        obs.register_at(cfg)

        assert hasattr(obs, "other")
        assert not hasattr(obs, "other_setting")

        obs.set_settings_to_callables({"other": obs.other_method})
        assert not hasattr(obs, "other")
        assert hasattr(obs, "other_setting")
        assert obs.other_setting == "Other Inital State"

        cfg.save_settings({"content": "New State", "other": "New Other State", "unrelated": "Unrelated"})
        assert obs.content == "New State"
        assert obs.other_setting == "New Other State"

    @staticmethod
    def test_settings_to_callables_keep_attr(tmp_path) -> None:
        """Test redirecting a setting to a Callable while keeping the created attribute."""
        cfg = _BaseSettingsManager(tmp_path)
        obs = _BaseSettingsObserver({"content": "Initial State", "other": "Other Inital State"})
        obs.register_at(cfg)

        assert hasattr(obs, "other")
        obs.set_settings_to_callables({"other": obs.other_method}, keep_attr=True)
        assert hasattr(obs, "other")

    @staticmethod
    def test_invalid_callable() -> None:
        """Test error if settings_to_callables entries are invalid."""
        obs = _BaseSettingsObserver({"content": "Initial State", "number": 42})
        settings_to_callables = {
            "content": obs.other_method,
            "invalid_1": obs.other_method,
            "invalid_2": obs.other_method,
        }

        with pytest.raises(ValueError, match=r".*\['invalid_1', 'invalid_2'\].*"):
            obs.set_settings_to_callables(settings_to_callables)

    @staticmethod
    def test_not_callable() -> None:
        """Test error if settings_to_callables value is not actually callable."""
        obs = _BaseSettingsObserver({"content": "Initial State", "number": 42, "include_thing": True})
        settings_to_callables = {"content": obs.other_method, "number": 404, "include_thing": False}
        with pytest.raises(ValueError, match=r".* \[404, False\]"):
            obs.set_settings_to_callables(settings_to_callables)  # type: ignore[arg-type]

    @staticmethod
    def test_setting_not_found(tmp_path) -> None:
        """Test if observer resets setting back to default state if not found."""
        cfg = _BaseSettingsManager(tmp_path)
        obs = _BaseSettingsObserver({"content": "Initial State"})
        obs.content = "New State"
        obs.register_at(cfg)
        cfg.save_setting("unrelated", "Unrelated")  # Otherwise file will not exist.
        cfg.load_setting("content")

        assert obs.content == "Initial State"


class TestSettingsObserverSavable:
    """Additional tests for interaction between SettingsManager and SettingsObserverSavable."""

    @staticmethod
    def test_register_multiple(tmp_path, caplog) -> None:
        """Test warning when registering multiple SettingsObserverSavable instances for the same setting."""
        cfg = _BaseSettingsManager(tmp_path)

        obs_regular = _BaseSettingsObserver({"content": "Initial State"})
        obs_savable_1 = _BaseSettingsObserverSavable({"content": "Initial State"})
        obs_savable_2 = _BaseSettingsObserverSavable({"content": "Initial State"})

        obs_regular.register_at(cfg)
        obs_savable_1.register_at(cfg)
        obs_savable_2.register_at(cfg)

        setting = cfg._observed_settings.get("content")
        assert setting is not None
        assert isinstance(setting, list)
        assert len(setting) == 2

        records = caplog.records
        assert len(records) == 3
        assert records[2].levelname == "WARNING"
        msg = records[2].getMessage()
        assert "only one" in msg
        assert "content" in msg

    @staticmethod
    def test_single_setting(tmp_path) -> None:
        """Test single setting that can have its state saved and loaded."""
        obs = _BaseSettingsObserverSavable({"content": "Initial State"})
        cfg = _BaseSettingsManager(tmp_path)
        obs.register_at(cfg)

        cfg.save_setting("content", "New State")
        assert obs.content == "New State"

        obs.content = "Self Changed State"
        cfg.check_state("content")
        assert cfg.load_setting("content") == "Self Changed State"

    @staticmethod
    def test_multiple_settings(tmp_path) -> None:
        """Test mustiple settings that can have their state saved and loaded."""
        obs = _BaseSettingsObserverSavable({"content": "Initial State", "number": 42, "include_thing": True})
        cfg = _BaseSettingsManager(tmp_path)
        obs.register_at(cfg)

        cfg.save_settings({"content": "New State", "number": 2, "include_thing": False})
        assert obs.content == "New State"
        assert obs.number == 2
        assert not obs.include_thing

        obs.content = "Self Changed State"
        obs.number = 123
        obs.include_thing = True

        cfg.check_states_all()
        assert cfg.load_setting("content") == "Self Changed State"
        assert cfg.load_setting("number") == 123
        assert cfg.load_setting("include_thing")

    @staticmethod
    def test_update_none(tmp_path, caplog) -> None:
        """Test warning when there are no observed settings to update."""
        cfg = _BaseSettingsManager(tmp_path)
        cfg.check_states_all()

        records = caplog.records
        assert len(records) == 1
        assert records[0].levelname == "WARNING"
        assert records[0].getMessage() == "No observers registered. Ignoring."

    @staticmethod
    def test_update_wrong_setting(tmp_path, caplog) -> None:
        """Test warning when updating setting without observers."""
        obs = _BaseSettingsObserverSavable({"content": "Initial State"})
        cfg = _BaseSettingsManager(tmp_path)
        obs.register_at(cfg)

        cfg.save_setting("other", "Other State")
        cfg.check_state("other")

        records = caplog.records
        assert len(records) == 3
        assert records[2].levelname == "WARNING"
        msg = records[2].getMessage()
        assert "No observers registered" in msg
        assert "other" in msg

    @staticmethod
    def test_update_not_savable(tmp_path, caplog) -> None:
        """Test warning when updating setting that has a regular observer, but no savable observer."""
        obs_regular = _BaseSettingsObserver({"other": "Initial State"})
        obs_savable = _BaseSettingsObserverSavable({"content": "Initial State"})
        cfg = _BaseSettingsManager(tmp_path)
        obs_regular.register_at(cfg)
        obs_savable.register_at(cfg)

        cfg.save_setting("other", "New State")
        cfg.check_state("other")

        assert obs_regular.other == "New State"

        records = caplog.records
        assert len(records) == 4
        assert records[3].levelname == "WARNING"
        msg = records[3].getMessage()
        assert "No SettingsObserverSavable instance" in msg
        assert "other" in msg

    @staticmethod
    def test_update_mixed(tmp_path) -> None:
        """Test updating a regular observer with the value of another savable observer."""
        obs_regular = _BaseSettingsObserver({"content": "Initial State"})
        obs_savable = _BaseSettingsObserverSavable({"content": "Initial State"})
        cfg = _BaseSettingsManager(tmp_path)
        obs_regular.register_at(cfg)
        obs_savable.register_at(cfg)

        obs_savable.content = "New State"
        assert obs_regular.content == "Initial State"

        cfg.check_states_all()
        assert obs_regular.content == "New State"

    @staticmethod
    def test_callable(tmp_path) -> None:
        """Test single setting that is redirected to a callable for both loading and saving."""
        obs = _BaseSettingsObserverSavable({"other": "Initial State"})
        obs.set_settings_to_callables({"other": obs.set_other})
        obs.set_callables_to_settings({"other": obs.get_other})
        cfg = _BaseSettingsManager(tmp_path)
        obs.register_at(cfg)

        cfg.save_setting("other", "New State")
        assert obs.other_setting == "New State"

        obs.other_setting = "Self Changed State"
        cfg.check_state("other")
        assert obs.other_setting == "Self Changed State"

        assert cfg.load_setting("other") == "Self Changed State"

    @staticmethod
    def test_not_callable() -> None:
        """Test error if callables_to_settings value is not actually callable."""
        obs = _BaseSettingsObserverSavable({"content": "Initial State", "number": 42, "include_thing": True})
        callables_to_settings = {"content": obs.get_other, "number": 404, "include_thing": False}
        with pytest.raises(ValueError, match=r".* \[404, False\]"):
            obs.set_callables_to_settings(callables_to_settings)  # type: ignore[arg-type]

    @staticmethod
    def test_qt_checkbox(tmp_path, qtbot) -> None:
        """Test loading and saving state of an actual QCheckbox widget."""

        class _TestQCheckBox(SettingsObserverSavable, QCheckBox):
            def __init__(self, settings) -> None:
                """Initialize."""
                QCheckBox.__init__(self)
                super().__init__(settings)
                self.set_settings_to_callables({"box_checked": self.setChecked})
                self.set_callables_to_settings({"box_checked": self.isChecked})

        cb = _TestQCheckBox(settings={"box_checked": True})
        qtbot.addWidget(cb)
        assert cb.isChecked()
        cfg = _BaseSettingsManager(tmp_path)
        cb.register_at(cfg)

        cfg.save_setting("box_checked", value=False)
        assert not cb.isChecked()
        assert not cfg.load_setting("box_checked")

        cb.setChecked(True)
        cfg.check_states_all()
        assert cfg.load_setting("box_checked")
