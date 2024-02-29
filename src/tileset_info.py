from pathlib import Path

from compose import ComposingException, Tileset, read_properties
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QWidget,
)

from main import ICON_PATH


class TilesetInfo(QFrame):
    class FileStatusEntry(QWidget):
        def __init__(self, file_name: str = None, optional: bool = False):
            super().__init__()

            layout = QHBoxLayout()
            self.setLayout(layout)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setAlignment(Qt.AlignmentFlag.AlignRight)
            layout.setSpacing(0)
            if file_name:
                font = QFont()
                font.setPointSize(10)
                font.setBold(True)
                layout.addWidget(QLabel(file_name, font=font))

            self.icon_true = QPixmap(ICON_PATH.joinpath("valid.png"))
            if optional:
                self.icon_false = QPixmap(ICON_PATH.joinpath("optional_missing.png"))
            else:
                self.icon_false = QPixmap(ICON_PATH.joinpath("invalid.png"))
            self.icon_display = QLabel()
            self.icon_display.setPixmap(self.icon_false)
            layout.addWidget(self.icon_display)

        def set_valid(self, valid: bool):
            if valid:
                self.icon_display.setPixmap(self.icon_true)
            else:
                self.icon_display.setPixmap(self.icon_false)

    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.Box)

        font = QFont()
        font.setPointSize(10)
        font.setBold(True)

        self.layout = QGridLayout()
        self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        self.layout.addWidget(QLabel("Name: ", font=font), 0, 0)
        self.label_prop_name = QLabel(font=font)
        self.label_prop_name.setMinimumWidth(250)
        self.layout.addWidget(self.label_prop_name, 0, 1)
        self.layout.addWidget(QLabel("View: ", font=font), 1, 0)
        self.label_prop_view = QLabel(font=font)
        self.layout.addWidget(self.label_prop_view, 1, 1)

        self.layout.addWidget(QLabel("Required:", font=font), 0, 2)
        self.valid_tileset = self.FileStatusEntry("tileset.txt")
        self.layout.addWidget(self.valid_tileset, 0, 3)
        self.valid_tile_info = self.FileStatusEntry("tile_info.json")

        self.layout.addWidget(QLabel("Optional:", font=font), 1, 2)
        self.layout.addWidget(self.valid_tile_info, 0, 4)
        self.valid_layering = self.FileStatusEntry("layering.json", optional=True)
        self.layout.addWidget(self.valid_layering, 1, 3)
        self.valid_fallback = self.FileStatusEntry("fallback.png", optional=True)
        self.layout.addWidget(self.valid_fallback, 1, 4)

    def read_tileset_info(self, src_dir: str, out_dir):
        """
        Read tileset properties and tilesheet names. Update info display.
        """
        try:
            prop = read_properties(f"{src_dir}/tileset.txt")
            self.label_prop_name.setText(prop["NAME"])
            self.label_prop_view.setText(prop["VIEW"])
            self.tileset = True
        except FileNotFoundError:
            self.label_prop_name.setText("[Invalid Tileset Path]")
            self.label_prop_view.setText("[Invalid Tileset Path]")
            self.tileset = False
        self.valid_tileset.set_valid(self.tileset)
        # extract sheet names
        try:
            info = Tileset(Path(src_dir), Path(src_dir)).info
            result = []
            for entry in info:
                result.append(str(list(entry.keys())[0]))
            self.tilesheets = result[1:]
            self.tile_info = True
        except ComposingException:
            self.tilesheets = []
            self.tile_info = False
        self.out_is_default = not out_dir or "/default_compose_output" in out_dir

        self.valid_tile_info.set_valid(self.tile_info)
        self.valid_layering.set_valid((Path(src_dir) / "layering.json").is_file())
        self.valid_fallback.set_valid((Path(src_dir) / "fallback.png").is_file())
