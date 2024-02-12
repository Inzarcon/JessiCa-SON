import json

from compose_logger import get_logger
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

log = get_logger("compose")


class ProfileManager(QWidget):
    sig_loaded = Signal()

    def __init__(self, cfg_path, widgets: list[QWidget]):
        super().__init__()
        self.label = QLabel("Profile:")
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.label.setFont(font)

        self.drop_down = QComboBox()
        self.drop_down.setMinimumWidth(150)
        self.input_profile_name = QLineEdit()
        self.input_profile_name.setPlaceholderText("Set profile name:")
        self.input_profile_name.setMaximumWidth(200)
        self.btn_save = QPushButton("Save Profile")
        self.btn_save.setMinimumWidth(115)
        self.btn_set_as_default = QPushButton("Set as default profile")

        layout = QHBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.drop_down)
        layout.addWidget(QLabel("Set Profile Name:"))
        layout.addWidget(self.input_profile_name)
        layout.addWidget(self.btn_save)
        layout.addWidget(self.btn_set_as_default)
        layout.addStretch()
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.btn_save.pressed.connect(self.save)
        self.btn_set_as_default.pressed.connect(self.set_default)
        self.drop_down.currentIndexChanged.connect(self.on_drop_down_change)
        self.input_profile_name.textChanged.connect(self.on_input_text_change)

        self.config_path = cfg_path
        self.widgets = widgets
        self.entries = None

        self.scan_profiles()
        self.load_default()
        self.on_input_text_change()

    # TODO: Refactor code before adding features. Works for now, but way too
    #       chaotic edge case handling.

    def on_input_text_change(self):
        cur_text = self.input_profile_name.text()
        if self.profile_exists(cur_text):
            self.btn_save.setText("Overwrite Profile")
        else:
            self.btn_save.setText("Create new Profile")

    def on_drop_down_change(self):
        new = self.drop_down.currentText()
        if self.input_profile_name.text() != new:
            self.load(new)
            self.input_profile_name.setText(new)
        self.btn_set_as_default.setEnabled(not self.is_default(new))

    def scan_profiles(self):
        files = self.config_path.glob("*.json")
        # TODO: Cleaner way of filtering out cur_default.json pointer.
        files = [
            file.parts[-1][:-5] for file in files if "cur_default.json" not in str(file)
        ]
        self.drop_down.addItems(files)

    def set_default(self):
        # TODO: Exception handling and validation.
        file_path = self.config_path / "cur_default.json"
        self.config_path.mkdir(exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump({"cur_default": self.input_profile_name.text()}, file, indent=4)
        self.btn_set_as_default.setEnabled(False)

    def save(self):
        cur_input = self.input_profile_name.text()
        entries = {
            entry[0]: entry[1]
            for widget in self.widgets
            if (entry := self._handle_widget_write(widget))
        }
        file_path = self.config_path / f"{cur_input}.json"
        # TODO: Exception handling.
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(entries, file, indent=4)
        if self.drop_down.findText(cur_input) < 0:  # New entry
            self.drop_down.addItem(cur_input)
            self.drop_down.setCurrentIndex(self.drop_down.findText(cur_input))
            self.on_input_text_change()

    def load_default(self):
        # TODO: Exception handling.
        if (self.config_path / "cur_default.json").is_file():
            entry = self._load_json(self.config_path / "cur_default.json")
        else:  # First start or otherwise missing -> Generate default config
            entry = {"cur_default": "Default"}
            self.input_profile_name.setText("Default")
            self.set_default()
            self.save()
        self.load(entry.get("cur_default"))

    def load(self, profile_name):
        file_path = self.config_path / f"{profile_name}.json"
        self.entries = self._load_json(file_path)
        self.input_profile_name.setText(profile_name)
        self.drop_down.setCurrentText(profile_name)
        for widget in self.widgets:
            try:
                self._handle_widget_load(widget)
            except TypeError as exception:
                log.error(
                    "%s\n in %s property %s",
                    exception,
                    file_path,
                    widget.objectName(),
                )
        self.sig_loaded.emit()

    def is_default(self, profile_name):
        return profile_name == self._load_json(
            self.config_path / "cur_default.json"
        ).get("cur_default")

    def profile_exists(self, profile_name):
        return (self.config_path / f"{profile_name}.json").is_file()

    @staticmethod
    def _save_json(file_path, entries):
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(entries, file, indent=4)

    @staticmethod
    def _load_json(file_path):
        try:
            with open(file_path, encoding="utf-8") as file:
                return json.load(file)
        except json.decoder.JSONDecodeError as exception:
            log.error("JSONDecodeError %s: %s", file_path, exception)
        except FileNotFoundError:
            log.error(
                "Profile %s not found. Starting with initial " "configuration.",
                file_path,
            )

    @staticmethod
    def _handle_widget_write(widget):
        if not (name := widget.objectName()):
            return None
        if isinstance(widget, QCheckBox):
            return name, widget.isChecked()
        if isinstance(widget, QLineEdit):  # noqa: RET503
            return name, widget.text()

    def _handle_widget_load(self, widget):
        name = widget.objectName()
        if not self.entries or not name or name not in self.entries:
            return
        if isinstance(widget, QCheckBox):
            widget.setChecked(self.entries.get(name))
        if isinstance(widget, QLineEdit):
            widget.setText(self.entries.get(name))
