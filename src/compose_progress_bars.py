from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QGridLayout, QLabel, QProgressBar, QWidget


class ComposeProgressBars(QWidget):
    def __init__(self):
        super().__init__()
        self.hide()

        self.total_count = 0

        self.label_loaded = QLabel("Sprites loaded:")
        self.progress_loaded = QProgressBar()
        self.progress_loaded.setValue(0)
        self.progress_loaded.setAlignment(Qt.AlignCenter)
        self.set_color(self.progress_loaded, "#4175c4")

        self.label_composed = QLabel("Sprites composed:")
        self.progress_composed = QProgressBar()
        self.progress_composed.setValue(0)
        self.progress_composed.setAlignment(Qt.AlignCenter)

        self.composed_cur = {}
        self.composed_pngnums = {}
        self.subset = ()

        # TODO: Refactor to not be duplicate code. -> General utility function?
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.label_loaded.setFont(font)
        self.label_composed.setFont(font)

        layout = QGridLayout()
        self.setLayout(layout)
        layout.addWidget(self.label_loaded, 0, 0)
        layout.addWidget(self.progress_loaded, 0, 1)
        layout.addWidget(self.label_composed, 1, 0)
        layout.addWidget(self.progress_composed, 1, 1)
        layout.setContentsMargins(0, 0, 0, 0)

        self.reset()  # TODO Refactor duplicates away and call from __init__

    def set_total(self, tilesheet_sprites: list[str], total_sprites: int):
        self.composed_cur = {tilesheet: 0 for tilesheet in tilesheet_sprites}
        self.composed_pngnums = tilesheet_sprites
        self.progress_loaded.setRange(0, total_sprites)
        self.progress_composed.setRange(0, self.weighted_sum(True))

    def weighted_sum(self, total=False):
        items = self.composed_cur.items()
        if total:
            items = [(name, 100) for name, _ in items]
        return sum((percent * self.composed_pngnums[name] for name, percent in items))

    def update_percent(self, sheet_name, percent: int) -> None:
        self.composed_cur[sheet_name] = percent
        self.progress_composed.setValue(self.weighted_sum())

    def set_color(self, which: QProgressBar, color: str = None):
        color = color if color else "#669ff5"
        css = r"QProgressBar::chunk {background: " + color + "}"
        which.setStyleSheet(css)

    def update_image(self) -> None:
        self.total_count += 1
        self.progress_loaded.setValue(self.total_count)

    def reset(self):
        """Reset to initial state."""
        self.hide()
        self.progress_loaded.setValue(0)
        self.progress_loaded.setRange(-1, 0)
        self.progress_composed.setValue(0)
        self.total_count = 0
