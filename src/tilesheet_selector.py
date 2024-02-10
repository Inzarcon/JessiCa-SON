"""Module for the TilesheetSelector class."""

from common_utils import delete_layout_widgets, get_layout_widgets
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QGridLayout, QVBoxLayout, QWidget

N_COLS = 6  # TODO: Make this more dynamic.


class TilesheetSelector(QWidget):
    """
    QWidget for optionally selecting a subset of tilesheets to compose.
    Enabling the main checkbox opens a selection grid.
    """

    class SelectorGrid(QWidget):
        """Subclass defining the main grid and its behavior."""

        def __init__(self, tilesheet_names: list[str], parent):
            super().__init__()
            self.layout = QGridLayout()
            self.setLayout(self.layout)
            self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            count = 0
            for name in tilesheet_names:
                if name == "fallback.png":
                    continue
                row, col = divmod(count, N_COLS)
                widget = QCheckBox(name)
                self.layout.addWidget(widget, row, col)
                widget.stateChanged.connect(parent._on_grid_change)
                count += 1

        def grid_state(self):
            """Return a list of the currently selected tilesheet names."""
            result = []
            for widget in get_layout_widgets(self.layout):
                if widget.isChecked():
                    result.append(widget.text())
            return result

    sig_grid_change = Signal(str)

    def __init__(self):
        super().__init__()
        self.main_checkbox = QCheckBox("Compose only specific tilesheet(s)")
        self.main_checkbox.setToolTip(
            "If enabled, choose tilesheet(s) to be composed. The\n"
            "remaining tilesheets will be skipped.\n"
            "(Note: All JSON entries and sprite file names are still\n"
            "processed in order to generate a valid configuration.)"
        )
        self.main_checkbox.stateChanged.connect(self._on_main_change)
        self.selector_grid = None

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.main_checkbox)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setLayout(self.layout)
        self.layout.setContentsMargins(0, 0, 0, 0)

    def set_entries(self, tilesheet_names: list[str]):
        """Define the set of selectable tilesheet names."""
        self.clear_entries()
        self.selector_grid = self.SelectorGrid(tilesheet_names, self)
        self.layout.addWidget(self.selector_grid)
        if not self.main_checkbox.isChecked():
            self.selector_grid.hide()

    def clear_entries(self):
        """Delete the selector grid if one exists."""
        if self.selector_grid:
            delete_layout_widgets(self.layout, except_indeces=[0])

    def _on_main_change(self, state):
        """Called when the main checkbox was clicked."""
        try:
            if state:
                self.selector_grid.show()
            else:
                self.selector_grid.hide()

            if self.main_checkbox.isChecked():
                self._on_grid_change()
            else:
                self.sig_grid_change.emit("Ready for composing.")

        except AttributeError:
            self.sig_grid_change.emit("No valid tileset selected.")
            self.clear_entries()
        except RuntimeError as e:
            # TODO: Refactor to prevent this from happening in the first place.
            if str(e) != "Internal C++ object (SelectorGrid) already deleted.":
                raise

    def _on_grid_change(self):
        """Called when a selector grid entry was clicked."""
        state_string = ", ".join(self.grid_state())
        if not state_string:
            self.sig_grid_change.emit(
                "No tilesheet selected; will compose whole tileset. "
                'Enable the "Only JSON" checkbox instead if you want to '
                "completely skip tilesheet composing."
            )
        else:
            self.sig_grid_change.emit(f"Ready for composing {state_string}.")

    def grid_state(self):
        """Return a list of the currently selected tilesheet names."""
        return self.selector_grid.grid_state()
