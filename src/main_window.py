"""
Module containing the main application window where all subcomponents are used.
"""

import json
from pathlib import Path

from common_utils import enable_widgets
from compose import (
    ComposeRunner,
    ComposeSignalType,
    ComposingException,
    Tileset,
    connect_compose_signal,
    read_properties,
)
from compose_logger import get_logger
from compose_message_box import ComposeMessageBox
from compose_progress_bars import ComposeProgressBars
from PySide6.QtCore import Qt, QThreadPool, QUrl, Signal
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QTextBrowser,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from qdarktheme import setup_theme
from tilesheet_selector import TilesheetSelector

log = get_logger("compose")

# TODO: Cleaner way and/or setting in main.py instead.
# TODO: Also consider Qt's resource management. (though overkill at this stage)
root_path = Path(__file__).resolve().parents[1]
cfg_path = root_path.joinpath(".config")
icon_path = root_path.joinpath("resources/icons")


class ProfileManager(QWidget):
    sig_loaded = Signal()

    def __init__(self, widgets: list[QWidget]):
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
    # chaotic edge case handling.

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


# TODO: Refactor status labels into their own QWidget Class. Code is getting
# all over the place.
class MainWindow(QMainWindow):
    """Main application window itself"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            "JessiCa: Serpents Obstruct None (Compose Module Standalone)"
        )
        self.resize(1200, 600)

        self.btn_compose = QPushButton("Compose")
        self.btn_compose.pressed.connect(self.start_compose)
        self.btn_compose.setEnabled(False)
        icon_compose = QPixmap(icon_path.joinpath("compose.png"))
        self.btn_compose.setIcon(icon_compose)

        self.cb_use_all = QCheckBox("Use All", objectName="use_all")
        self.cb_use_all.setChecked(True)
        # TODO: Utility function for tooltip texts. Or load from JSON file?
        self.cb_use_all.setToolTip(
            "Automatically generate JSON entries for unreferenced sprites. "
            "Filename defines the ID name.\nFor example, an unreferenced "
            '"snake.png" will be added for the game ID "snake".\n'
            "(Note: If the ID does not actually exist, the game ignores it.)"
        )
        self.cb_only_json = QCheckBox("Only JSON", objectName="only_json")
        self.cb_only_json.setToolTip(
            "Generate only tile_config.json. No actual spritesheets will\n"
            "be composed."
        )

        self.cb_format_json = QCheckBox("Format JSON", objectName="format_json")
        self.cb_format_json.setToolTip(
            "Format the resulting tile_config.json. If no json_formatter.exe "
            "is \nfound in the tools folder, the Python built-in formatter "
            "will be used."
        )

        self.btn_abort = QPushButton("Abort")
        self.btn_abort.setDisabled(True)
        self.btn_abort.pressed.connect(self.abort_compose)
        icon_abort = QPixmap(icon_path.joinpath("abort.png"))
        self.btn_abort.setIcon(icon_abort)

        self.label_src = QLabel("Source Directory:")
        self.btn_src_input = QPushButton("Select")
        self.btn_src_input.pressed.connect(self.on_source_input_click)
        self.src_input = QLineEdit(objectName="source_dir")
        self.src_input.textChanged.connect(self.read_tileset_info)

        self.label_out = QLabel("Output Directory:", objectName="output_dir")
        self.btn_out_input = QPushButton("Select")
        # TODO: Change naming as "output_input" may be confusing
        self.btn_out_input.pressed.connect(self.on_output_input_click)
        self.out_input = QLineEdit(objectName="output_dir")

        self.layout_input = QGridLayout()
        self.layout_input.addWidget(self.label_src, 0, 0)
        self.layout_input.addWidget(self.btn_src_input, 0, 1)
        self.layout_input.addWidget(self.src_input, 0, 2)
        self.layout_input.addWidget(self.label_out, 1, 0)
        self.layout_input.addWidget(self.btn_out_input, 1, 1)
        self.layout_input.addWidget(self.out_input, 1, 2)

        self.label = QLabel("Please select tileset source directory.")
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.label.setFont(font)

        self.layout_tileset_info = QGridLayout()
        self.layout_tileset_info.addWidget(QLabel("Tileset Name: ", font=font), 0, 0)
        self.label_prop_name = QLabel("[No tileset selected]")
        self.layout_tileset_info.addWidget(self.label_prop_name, 0, 1)
        self.layout_tileset_info.addWidget(QLabel("View Name: ", font=font), 1, 0)
        self.label_prop_view = QLabel("[No tileset selected]")
        self.layout_tileset_info.addWidget(self.label_prop_view, 1, 1)
        self.layout_tileset_info.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.tilesheet_selector = TilesheetSelector()

        self.status_bar = QStatusBar()
        self.status_bar.addPermanentWidget(self.label, 1)
        self.setStatusBar(self.status_bar)

        self.tilesheet_selector.sig_grid_change.connect(self.label.setText)
        self.compose_subset = []

        self.label_prop_name.setFont(font)
        self.label_prop_view.setFont(font)
        self.progress_bars = ComposeProgressBars()
        self.sprites_per_sheet_dict = {}
        self.sheet_count = 0

        self.message_box = ComposeMessageBox()

        # TODO: Move log switch to ComposeMessageBox
        self.cb_switch_log = QCheckBox("Show Raw Log")
        self.cb_switch_log.setToolTip("Show full, unformatted log.")
        self.cb_switch_log.toggled.connect(self.message_box.switch)

        log.handlers[0].formatter.connect_log(self.message_box.message_raw)

        connect_compose_signal(self.handle_compose_signal)
        self.runner = None

        self.control_widgets = [
            self.btn_compose,
            self.btn_abort,
            self.cb_use_all,
            self.cb_only_json,
            self.cb_format_json,
        ]
        self.layout_controls = QHBoxLayout()
        for widget in self.control_widgets:
            self.layout_controls.addWidget(widget)
        # Add widgets with own layout separately
        self.control_widgets.append(self.tilesheet_selector)
        self.control_widgets.append(self.btn_src_input)
        self.control_widgets.append(self.src_input)
        self.control_widgets.append(self.btn_out_input)
        self.control_widgets.append(self.out_input)

        self.layout_controls.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.profile_manager = ProfileManager(self.control_widgets)
        self.profile_manager.sig_loaded.connect(self.read_tileset_info)
        self.read_tileset_info()  # Alternatively connection within init.

        layout = QVBoxLayout()
        layout.addWidget(self.profile_manager)
        layout.addLayout(self.layout_tileset_info)
        layout.addLayout(self.layout_input)
        layout.addLayout(self.layout_controls)
        layout.addWidget(self.tilesheet_selector)
        layout.addWidget(self.message_box)
        layout.addWidget(self.cb_switch_log)
        layout.addWidget(self.progress_bars)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        window = QWidget()
        window.setLayout(layout)
        self.setCentralWidget(window)

        # TODO: Fix to QThread
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(1)

        # TODO: Find out why background-color is working only in standalone
        # version. Leave at white for now.
        css = "QToolTip {background-color: white; color: black;}"
        self.setStyleSheet(css)

        self.toolbar = QToolBar("Toolbar")
        toolbar_spacer = QWidget()
        toolbar_about_qt = QPushButton("About Qt")
        toolbar_licenses = QPushButton("Licenses")

        toolbar_spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        toolbar_about_qt.pressed.connect(lambda: QMessageBox().aboutQt(self))
        toolbar_licenses.pressed.connect(self.show_licenses)

        self.toolbar.addWidget(toolbar_spacer)
        self.toolbar.addWidget(toolbar_about_qt)
        self.toolbar.addWidget(toolbar_licenses)
        self.addToolBar(self.toolbar)

    def show_licenses(self):
        self.license_box = QTextBrowser()
        self.license_box.setWindowTitle("LICENSE.md")
        url = QUrl.fromLocalFile(root_path.joinpath("LICENSE.md"))
        self.license_box.setSource(url)
        self.license_box.resize(1000, 600)
        self.license_box.show()

    def on_source_input_click(self):
        """
        Called when source selection button was clicked. Open a file Dialog and
        handle result.
        """
        selection = QFileDialog.getExistingDirectory(caption="Open directory")
        self.src_input.setText(selection)

    def on_output_input_click(self):
        """
        Called when output selection button was clicked. Open a file Dialog and
        handle result.
        """
        selection = QFileDialog.getExistingDirectory(caption="Open directory")
        self.out_input.setText(selection)
        self.label.setText("Ready for composing.")

    def read_tileset_info(self):
        """
        Read tileset properties and tilesheet names.
        """
        try:
            prop = read_properties(f"{self.src_input.text()}/tileset.txt")
            self.label_prop_name.setText(prop["NAME"])
            self.label_prop_view.setText(prop["VIEW"])
        except FileNotFoundError:
            self.label_prop_name.setText("[Invalid Tileset Path]")
            self.label_prop_view.setText("[Invalid Tileset Path]")
            self.btn_compose.setEnabled(False)
            self.label.setText("No tile_info.json found in source directory.")
            return
        # extract sheet names
        try:
            info = Tileset(
                Path(self.src_input.text()), Path(self.out_input.text())
            ).info
            result = []
            for entry in info:
                result.append(str(list(entry.keys())[0]))
            self.tilesheet_selector.set_entries(result[1:])
            self.label.setText("Ready for composing.")
            self.btn_compose.setEnabled(True)
        except ComposingException:
            self.tilesheet_selector.clear_entries()
            self.btn_compose.setEnabled(False)
        out_was_default = "/default_compose_output" in self.out_input.text()
        if not self.out_input.text() or out_was_default:
            self.out_input.setText(f"{self.src_input.text()}/default_compose_output")
            self.label.setText(
                "Ready for composing into default output directory. "
                "Select the corresponding tileset in your game files as"
                " output to update it automatically."
            )

    def enable_controls(self, enable=True):
        """Shortcut for enabling/diabling the control widgets."""
        enable_widgets(self.control_widgets, enable)
        self.btn_abort.setEnabled(not enable)

    def start_compose(self):
        """Prepare and run the main composing routine."""
        self.enable_controls(False)
        self.message_box.clear()

        flags = []
        _ = not self.cb_use_all.isChecked() and flags.append("no_use_all")
        _ = self.cb_only_json.isChecked() and flags.append("only_json")
        _ = self.cb_format_json.isChecked() and flags.append("format_json")

        self.compose_subset = []
        # TODO: Catch exception just to be sure
        if self.tilesheet_selector.main_checkbox.isChecked():
            self.compose_subset = self.tilesheet_selector.grid_state()

        self.progress_bars.subset = self.compose_subset

        self.runner = ComposeRunner(
            self.src_input.text(),
            self.out_input.text(),
            flags,
            self.compose_subset,
        )
        self.runner.create_tileset()
        self.threadpool.start(self.runner.run)

    def abort_compose(self):
        """Request to stop the current composing process once possible."""
        self.btn_abort.setEnabled(False)
        self.enable_controls(True)
        self.label.setText("Aborting...")
        self.runner.exit()

    def closeEvent(self, _):
        """
        Called when application is quit. Abort composing process if it is
        running.
        """
        if self.runner:
            self.abort_compose()

    def handle_compose_signal(self, sig_type, message, replacements, msg_type):
        """Handle the different types of compose signals."""

        # TODO: Refactor to be cleaner, this is at risk of becoming code
        # spaghetti with further additions.
        if sig_type is ComposeSignalType.PROGRESS_PNGNUM:
            self.total_sprites = int(message)
            self.progress_bars.set_total(replacements, int(message))
        if sig_type is ComposeSignalType.PROGRESS_PERCENT:
            self.progress_bars.update_percent(message, replacements[0])
        if sig_type is ComposeSignalType.PROGRESS_IMAGE:
            self.progress_bars.update_image()
            self.sheet_count += 1
        if sig_type is ComposeSignalType.STATUS_MESSAGE:
            if replacements:
                self.label.setText(message.format(*replacements))
            else:
                self.label.setText(message)
        if sig_type is ComposeSignalType.LOADING:
            self.progress_bars.show()
        if sig_type is ComposeSignalType.FINISHED:
            self.label.setText(message)
            self.on_finished()
        if sig_type in [
            ComposeSignalType.WARNING_MESSAGE,
            ComposeSignalType.ERROR_MESSAGE,
        ]:
            self.message_box.message_pretty(sig_type, message, replacements, msg_type)

    def on_finished(self) -> None:
        """
        Called when composing has finished, whether successfully or aborted.
        Reset relevant widgets and variables to their initial state.
        """
        # TODO: Different text if there were warnings and/or errors.
        self.progress_bars.reset()

        self.message_box.show_suggestions()

        self.sprites_per_sheet_dict = {}

        self.runner = None
        self.sheet_count = 0

        self.enable_controls()


def run():
    """Start application and create main window."""
    app = QApplication([])
    setup_theme()
    window = MainWindow()
    window.show()
    app.exec()
