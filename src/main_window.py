"""
Module containing the main application window where all subcomponents are used.
"""
import version
from common_utils import enable_widgets
from compose import ComposeRunner, ComposeSignalType, connect_compose_signal
from compose_logger import get_logger
from compose_message_box import ComposeMessageBox
from compose_progress_bars import ComposeProgressBars
from profile_manager import ProfileManager
from PySide6.QtCore import QSize, Qt, QThreadPool, QUrl
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
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
from tileset_info import TilesetInfo
from tilesheet_selector import TilesheetSelector

from main import CFG_PATH, ICON_PATH, ROOT_PATH

log = get_logger("compose")


# TODO: Refactor status labels into their own QWidget Class. Code is getting
#       all over the place.
class MainWindow(QMainWindow):
    """Main application window itself"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"JessiCa: Serpents Obstruct None v{version.__version__}")
        self.resize(1200, 600)

        font = QFont()
        font.setPointSize(10)
        font.setBold(True)

        self.btn_compose = QPushButton("Compose")
        self.btn_compose.pressed.connect(self.start_compose)
        self.btn_compose.setEnabled(False)
        icon_compose = QPixmap(ICON_PATH.joinpath("compose.png"))
        self.btn_compose.setFixedSize(150, 60)
        self.btn_compose.setFont(font)
        self.btn_compose.setIcon(icon_compose)
        self.btn_compose.setIconSize(QSize(60, 60))
        self.btn_compose.setToolTip("Start composing process")

        self.btn_abort = QPushButton("Abort")
        self.btn_abort.setDisabled(True)
        self.btn_abort.pressed.connect(self.abort_compose)
        icon_abort = QPixmap(ICON_PATH.joinpath("abort.png"))
        self.btn_abort.setFixedSize(150, 60)
        self.btn_abort.setFont(font)
        self.btn_abort.setIcon(icon_abort)
        self.btn_abort.setIconSize(QSize(60, 60))
        self.btn_abort.setToolTip("Stop all composing threads once possible")

        self.layout_compose = QHBoxLayout()
        self.layout_compose.addWidget(self.btn_compose)
        self.layout_compose.addWidget(self.btn_abort)
        self.layout_compose.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.cb_use_all = QCheckBox("Use All", objectName="use_all")
        self.cb_use_all.setChecked(True)
        self.cb_use_all.setToolTip(
            'Add unused images with ID being their basename (i.e. without ".png")'
        )
        self.cb_only_json = QCheckBox("Only JSON", objectName="only_json")
        self.cb_only_json.setToolTip("Only output the tile_config.json")

        self.cb_format_json = QCheckBox("Format JSON", objectName="format_json")
        self.cb_format_json.setToolTip(
            "Format tile_config.json. Uses CDDA formatter if found,\n"
            "otherwise Python built-in formatter"
        )

        self.cb_fail_fast = QCheckBox("Fail Fast", objectName="fail_fast")
        self.cb_fail_fast.setToolTip("Stop immediately after an error has occurred")

        self.cb_obsolete_fillers = QCheckBox(
            "Show Obsolete Fillers", objectName="obsolete_fillers"
        )
        self.cb_obsolete_fillers.setToolTip("Warn about obsoleted fillers")

        self.cb_palette = QCheckBox("Palette", objectName="palette")
        self.cb_palette.setToolTip("Quantize all tilesheets to 8bpp colormaps")

        self.cb_palette_copies = QCheckBox(
            "Palette Copies", objectName="palette_copies"
        )
        self.cb_palette_copies.setToolTip(
            "Produce copies of tilesheets quantized to 8bpp colormaps"
        )

        self.label_src = QLabel("Source Directory:")
        self.btn_src_input = QPushButton("Select")
        self.btn_src_input.pressed.connect(self.on_source_input_click)
        self.src_input = QLineEdit(objectName="source_dir")
        self.src_input.textChanged.connect(self.update_tileset_info)

        self.label_out = QLabel("Output Directory:", objectName="output_dir")
        self.btn_out_input = QPushButton("Select")
        # TODO: Change naming as "output_input" may be confusing
        self.btn_out_input.pressed.connect(self.on_output_input_click)
        self.out_input = QLineEdit(objectName="output_dir")
        self.out_input.textChanged.connect(self.update_tileset_info)

        self.layout_input = QGridLayout()
        self.layout_input.addWidget(self.label_src, 0, 0)
        self.layout_input.addWidget(self.btn_src_input, 0, 1)
        self.layout_input.addWidget(self.src_input, 0, 2)
        self.layout_input.addWidget(self.label_out, 1, 0)
        self.layout_input.addWidget(self.btn_out_input, 1, 1)
        self.layout_input.addWidget(self.out_input, 1, 2)

        self.status_label = QLabel("Please select tileset source directory.")
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.status_label.setFont(font)

        self.tileset_info = TilesetInfo()

        self.tilesheet_selector = TilesheetSelector()

        self.status_bar = QStatusBar()
        self.status_bar.addPermanentWidget(self.status_label, 1)
        self.setStatusBar(self.status_bar)

        self.progress_bars = ComposeProgressBars()
        self.layout_compose.addWidget(self.progress_bars)

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
            self.cb_use_all,
            self.cb_only_json,
            self.cb_format_json,
            self.cb_fail_fast,
            self.cb_obsolete_fillers,
            self.cb_palette,
            self.cb_palette_copies,
        ]
        self.layout_controls = QHBoxLayout()
        for widget in self.control_widgets:
            self.layout_controls.addWidget(widget)
        # Add widgets with own layout separately
        self.control_widgets.append(self.btn_compose)
        self.control_widgets.append(self.btn_abort)
        self.control_widgets.append(self.tilesheet_selector)
        self.control_widgets.append(self.btn_src_input)
        self.control_widgets.append(self.src_input)
        self.control_widgets.append(self.btn_out_input)
        self.control_widgets.append(self.out_input)

        self.layout_controls.setAlignment(Qt.AlignmentFlag.AlignLeft)

        layout = QVBoxLayout()
        layout.addWidget(self.tileset_info, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(self.layout_input)
        layout.addLayout(self.layout_controls)
        layout.addWidget(self.tilesheet_selector)
        layout.addWidget(self.message_box)
        layout.addWidget(self.cb_switch_log)
        layout.addLayout(self.layout_compose)

        window = QWidget()
        window.setLayout(layout)
        self.setCentralWidget(window)

        # TODO: Fix to QThread
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(1)

        # TODO: Find out why background-color is working only in standalone
        #       version. Leave at white for now.
        css = "QToolTip {background-color: white; color: black;}"
        self.setStyleSheet(css)

        self.profile_manager = ProfileManager(CFG_PATH, self.control_widgets)
        self.profile_manager.sig_loaded.connect(self.update_tileset_info)
        self.update_tileset_info()  # Alternatively connection within init.

        spacer = QWidget()
        about_qt = QPushButton("About Qt")
        licenses = QPushButton("Licenses")

        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        about_qt.pressed.connect(lambda: QMessageBox().aboutQt(self))
        licenses.pressed.connect(self.show_licenses)

        self.toolbar = QToolBar("Toolbar")
        self.toolbar.setMovable(False)
        self.toolbar.addWidget(self.profile_manager)
        self.toolbar.addWidget(spacer)
        self.toolbar.addWidget(about_qt)
        self.toolbar.addWidget(licenses)
        self.addToolBar(self.toolbar)

    def show_licenses(self):
        self.license_box = QTextBrowser()
        self.license_box.setWindowTitle("LICENSE.md")
        url = QUrl.fromLocalFile(ROOT_PATH.joinpath("LICENSE.md"))
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
        self.status_label.setText("Ready for composing.")

    def update_tileset_info(self):
        self.tileset_info.read_tileset_info(
            self.src_input.text(), self.out_input.text()
        )
        valid = self.tileset_info.tileset and self.tileset_info.tile_info
        self.btn_compose.setEnabled(valid)
        if valid:
            self.tilesheet_selector.set_entries(self.tileset_info.tilesheets)
            self.status_label.setText("Ready for composing.")
        else:
            self.tilesheet_selector.clear_entries()
            if self.tileset_info.tileset:
                self.status_label.setText("Invalid or missing tile_info.json.")
            else:
                self.status_label.setText("Invalid or missing tileset.txt.")

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
        _ = self.cb_obsolete_fillers.isChecked() and flags.append("obsolete_fillers")
        _ = self.cb_fail_fast.isChecked() and flags.append("fail_fast")
        _ = self.cb_palette.isChecked() and flags.append("palette")
        _ = self.cb_palette_copies.isChecked() and flags.append("palette_copies")

        # TODO: Catch exception just to be sure
        if self.tilesheet_selector.main_checkbox.isChecked():
            self.compose_subset = self.tilesheet_selector.grid_state()
        else:
            self.compose_subset = self.tileset_info.tilesheets

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
        self.runner.request_abort(by_user=True)

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
        #       spaghetti with further additions.
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
                self.status_label.setText(message.format(*replacements))
            else:
                self.status_label.setText(message)
        if sig_type is ComposeSignalType.LOADING:
            self.progress_bars.show()
        if sig_type is ComposeSignalType.FINISHED:
            self.status_label.setText(message)
            self.on_finished()
        if sig_type in [
            ComposeSignalType.WARNING_MESSAGE,
            ComposeSignalType.ERROR_MESSAGE,
            ComposeSignalType.CRITICAL_MESSAGE,
        ]:
            self.message_box.message_pretty(sig_type, message, replacements, msg_type)

    def on_finished(self) -> None:
        """
        Called when composing has finished, whether successfully or aborted.
        Reset relevant widgets and variables to their initial state.
        """
        self.progress_bars.reset()

        self.message_box.show_suggestions()

        self.sprites_per_sheet_dict = {}

        self.runner = None
        self.sheet_count = 0

        self.btn_abort.setEnabled(False)
        self.enable_controls(True)


def run():
    """Start application and create main window."""
    app = QApplication([])
    setup_theme()
    window = MainWindow()
    window.show()
    app.exec()
