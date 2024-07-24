import json
import re
from pathlib import Path

from utils.widget_utils import set_widgets_visible
from utils.logger import get_logger
from pynput import keyboard
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)

log = get_logger("Compose")

# TODO: Put JSON stuff and main settings.json into separate module.
#       Currently clashes with ProfileManager and is very messy.
# TODO: Create QWidget for Compose/Abort buttons, handle this better than the
#       "self.parent.parent" below.


class HotKeyManager(QWidget):
    sig_updated = Signal(str, str)

    class HotkeyThread(QThread):
        """Thread for capturing keyboard shortcuts. Using pynput since QShortcut
        doesn't work when window is inactive.
        """

        def __init__(self, parent, compose_hk, abort_hk):
            super().__init__(parent)
            self.compose_hk = compose_hk
            self.abort_hk = abort_hk

        def run(self):
            with keyboard.GlobalHotKeys(
                {
                    self.compose_hk: self.parent.parent.start_compose_hotkey,
                    self.abort_hk: self.parent.parent.btn_abort.click,
                }
            ) as self.hk:
                self.hk.join()

        def quit(self):
            self.hk.stop()
            super().quit()

    def __init__(self, cfg_path):
        super().__init__()
        self.hotkey_thread = None
        self.settings_path = cfg_path / "settings.json"

        layout = QGridLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.btn_set = QPushButton("Set Hotkeys")
        self.btn_set.setFixedSize(80, 30)
        self.btn_set.pressed.connect(self._on_button_pressed)
        layout.addWidget(self.btn_set, 0, 0, 2, 1)

        size_policy = QSizePolicy()
        size_policy.setRetainSizeWhenHidden(True)

        self.label_compose = QLabel("Compose")
        layout.addWidget(self.label_compose, 0, 1)
        self.input_compose = QLineEdit("")
        self.input_compose.setMaximumWidth(120)
        self.input_compose.setSizePolicy(size_policy)
        layout.addWidget(self.input_compose, 0, 2)
        self.error_compose = QLabel("Invalid")
        self.error_compose.setStyleSheet("color: red")
        layout.addWidget(self.error_compose, 0, 3)

        self.label_abort = QLabel("Abort")
        layout.addWidget(self.label_abort, 1, 1)
        self.input_abort = QLineEdit("")
        self.input_abort.setMaximumWidth(120)
        self.input_abort.setSizePolicy(size_policy)
        layout.addWidget(self.input_abort, 1, 2)
        self.error_abort = QLabel("Invalid")
        self.error_abort.setStyleSheet("color: red")
        layout.addWidget(self.error_abort, 1, 3)

        self.nested_widgets = [
            self.label_compose,
            self.input_compose,
            self.label_abort,
            self.input_abort,
        ]

        set_widgets_visible(self.nested_widgets, visible=False)

        self.setLayout(layout)

    def setup(self):
        """Bandaid fix since this must run after ProfileManager is initialized."""
        if not Path(self.settings_path).is_file():
            self._save_json(self.settings_path, {})

        settings = self._load_json(self.settings_path)
        if "compose_hk" not in settings:
            settings["compose_hk"] = "Alt+F7"
        if "abort_hk" not in settings:
            settings["abort_hk"] = "Alt+F8"
        self._save_json(self.settings_path, settings)

        compose_hk, abort_hk = settings.get("compose_hk"), settings.get("abort_hk")

        self.set_hotkeys(compose_hk, abort_hk)
        self.input_compose.setText(compose_hk)
        self.input_abort.setText(abort_hk)

        self.input_compose.textEdited.connect(self.on_input_change)
        self.input_abort.textEdited.connect(self.on_input_change)

        self.on_input_change()
        self.sig_updated.emit(compose_hk, abort_hk)

    def set_hotkeys(self, compose_hk, abort_hk):
        assert self._hotkey_is_valid(compose_hk)
        assert self._hotkey_is_valid(abort_hk)

        settings = self._load_json(self.settings_path)
        settings["compose_hk"] = compose_hk
        settings["abort_hk"] = abort_hk
        self._save_json(self.settings_path, settings)

        if self.hotkey_thread is not None:
            self.hotkey_thread.quit()

        self.hotkey_thread = self.HotkeyThread(self, self._preparse_hotkey(compose_hk), self._preparse_hotkey(abort_hk))
        self.hotkey_thread.parent = self  # Doesn't work with setParent for some reason
        self.hotkey_thread.start()

    def on_input_change(self):
        self.compose_key = self.input_compose.text()
        self.abort_key = self.input_abort.text()

        compose_valid = self._hotkey_is_valid(self.compose_key)
        abort_valid = self._hotkey_is_valid(self.abort_key)

        self._show_error(compose_valid, self.error_compose)
        self._show_error(abort_valid, self.error_abort)

        self.valid = compose_valid and abort_valid
        if self.valid:
            self.btn_set.setEnabled(True)
        else:
            self.btn_set.setEnabled(False)

    def _show_error(self, valid, label):
        if valid:
            label.hide()
        else:
            label.show()

    def _on_button_pressed(self):
        if self.input_compose.isVisible():
            self.btn_set.setText("Set Hotkeys")
            set_widgets_visible(self.nested_widgets, visible=False)
            self.set_hotkeys(self.compose_key, self.abort_key)
            self.sig_updated.emit(self.compose_key, self.abort_key)
        else:
            if self.hotkey_thread is not None:
                self.hotkey_thread.quit()  # Stop triggers while in config
            self.btn_set.setText("Apply")
            set_widgets_visible(self.nested_widgets)

    @staticmethod
    def _preparse_hotkey(hotkey):
        """Add "<" and ">" to modifier keys for pynput so user doesn't need to
        know about this requirement.
        """
        # TODO: Exhaustive and correct regex. Works for basic cases for now.
        modifier_keys_regex = r"^(ctrl)|^(shift)|^(alt)|^(f)\d+"
        keys = hotkey.split("+")
        keys = [f"<{key}>" if re.fullmatch(modifier_keys_regex, key, re.IGNORECASE) else key for key in keys]
        return "+".join(keys)

    @staticmethod
    def _hotkey_is_valid(hotkey):
        try:
            preparsed = HotKeyManager._preparse_hotkey(hotkey)
            keyboard.HotKey.parse(preparsed)
            # Require at least one modifier or F key to avoid hotkey triggering
            # on basic letters.
            return "<" in preparsed
        except ValueError:
            return False

    @staticmethod
    # TODO: Make part of common utils
    def _save_json(file_path, entries):
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(entries, file, indent=4)

    @staticmethod
    # TODO: Make part of common utils
    def _load_json(file_path):
        try:
            with open(file_path, encoding="utf-8") as file:
                return json.load(file)
        except json.decoder.JSONDecodeError as exception:
            log.error("JSONDecodeError %s: %s", file_path, exception)
        except FileNotFoundError:
            log.error(
                "%s not found. Starting with initial hotkey configuration.",
                file_path,
            )
