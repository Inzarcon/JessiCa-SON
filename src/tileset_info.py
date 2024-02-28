from pathlib import Path

from compose import ComposingException, Tileset, read_properties
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QGridLayout, QLabel, QWidget


class TilesetInfo(QWidget):
    def __init__(self):
        super().__init__()

        font = QFont()
        font.setPointSize(10)
        font.setBold(True)

        self.layout = QGridLayout()
        self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setLayout(self.layout)

        self.layout.addWidget(QLabel("Tileset Name: ", font=font), 0, 0)
        self.label_prop_name = QLabel("[No tileset selected]", font=font)
        self.layout.addWidget(self.label_prop_name, 0, 1)
        self.layout.addWidget(QLabel("View Name: ", font=font), 1, 0)
        self.label_prop_view = QLabel("[No tileset selected]", font=font)
        self.layout.addWidget(self.label_prop_view, 1, 1)

    def read_tileset_info(self, src_dir: str, out_dir):
        """
        Read tileset properties and tilesheet names. Update info display.
        """
        try:
            prop = read_properties(f"{src_dir}/tileset.txt")
            self.label_prop_name.setText(prop["NAME"])
            self.label_prop_view.setText(prop["VIEW"])
            self.src_tileset = True
        except FileNotFoundError:
            self.label_prop_name.setText("[Invalid Tileset Path]")
            self.label_prop_view.setText("[Invalid Tileset Path]")
            self.src_tileset = False
        # extract sheet names
        try:
            info = Tileset(Path(src_dir), Path(src_dir)).info
            result = []
            for entry in info:
                result.append(str(list(entry.keys())[0]))
            self.tilesheets = result[1:]
            self.src_tile_info = True
        except ComposingException:
            self.tilesheets = []
            self.src_tile_info = False
        self.out_is_default = not out_dir or "/default_compose_output" in out_dir
