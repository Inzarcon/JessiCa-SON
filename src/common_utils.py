"""
Various utility functions and shortcuts used throughout the application. At
the current time this mostly concerns operations on multiple QWidgets.
"""


from PySide6.QtWidgets import QWidget


def enable_widgets(widgets: list[QWidget], enabled: bool = True) -> None:
    """Enable or disable all widgets in a list of widgets."""
    for widget in widgets:
        widget.setEnabled(enabled)


def get_layout_widgets(layout):
    """Return all widget that are part of a layout."""
    return [layout.itemAt(i).wid for i in range(layout.count())]


# https://stackoverflow.com/a/13103617
def delete_layout_widgets(layout, except_indeces=None):
    """Delete all Widgets in a layout without deleting the layout itself."""
    for i in reversed(range(layout.count())):
        if i not in except_indeces:
            layout.itemAt(i).widget().deleteLater()
