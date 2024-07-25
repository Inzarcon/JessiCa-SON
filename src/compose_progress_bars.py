"""Module containing ComposeProgressBars component."""

from common.components.basic_widgets import FormattedQLabel
from PySide6.QtWidgets import QGridLayout, QProgressBar, QWidget


class ComposeProgressBars(QWidget):
    """Progress bars shown during composing process."""

    _cur_loaded: int
    _cur_composed: dict[str, int]
    _sprites_per_tilesheet: dict[str, int]
    _subset: tuple[str]

    def __init__(self) -> None:
        """Create ComposeProgressBars."""
        super().__init__()

        self.label_loaded = FormattedQLabel("Sprites loaded:", font_size=10, bold=True)
        self.progress_loaded = QProgressBar()
        self._set_color(self.progress_loaded, "#4175c4")

        self.label_composed = FormattedQLabel("Sprites composed:", font_size=10, bold=True)
        self.progress_composed = QProgressBar()
        self._set_color(self.progress_composed, "#669ff5")

        layout = QGridLayout()
        self.setLayout(layout)
        layout.addWidget(self.label_loaded, 0, 0)
        layout.addWidget(self.progress_loaded, 0, 1)
        layout.addWidget(self.label_composed, 1, 0)
        layout.addWidget(self.progress_composed, 1, 1)
        layout.setContentsMargins(0, 0, 0, 0)

        self.reset()

    def setup(self, sprites_per_tilesheet: dict[str, int], total_sprites: int) -> None:
        """Set up the progress bars for the next run based on the given sprite numbers."""
        self._cur_composed = {tilesheet: 0 for tilesheet in sprites_per_tilesheet}
        self._sprites_per_tilesheet = sprites_per_tilesheet
        self.progress_loaded.setRange(0, total_sprites)
        self.progress_composed.setRange(0, total_sprites)
        self.show()

    def set_subset(self, subset: tuple[str]) -> None:
        """Set the subset of tilesheets to compose."""
        self._subset = subset

    def _calc_sprites_composed(self) -> int:
        entries = list(self._cur_composed.items())
        # Weight by total number of sprites in each tilesheet.
        return int(sum((percent * self._sprites_per_tilesheet[name] for name, percent in entries)) / 100)

    def update_percent(self, sheet_name: str, percent: int) -> None:
        """Update percentage of sprites composed so far for a specific tilesheet."""
        self._cur_composed[sheet_name] = percent
        self.progress_composed.setValue(self._calc_sprites_composed())

    def _set_color(self, progress_bar: QProgressBar, color: str) -> None:
        css = r"QProgressBar::chunk {background: " + color + "}"
        progress_bar.setStyleSheet(css)

    def increment_loaded(self) -> None:
        """Increment the counter for sprites loaded so far."""
        self._cur_loaded += 1
        self.progress_loaded.setValue(self._cur_loaded)

    def reset(self) -> None:
        """Reset to initial state."""
        self.hide()
        self.progress_loaded.setValue(0)
        self.progress_composed.setValue(0)
        self._cur_loaded = 0
