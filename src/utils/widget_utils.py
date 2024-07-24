"""Shortcuts for operations on multiple QWidgets."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QLayout, QWidget


def set_widgets_enabled(widgets: list[QWidget], *, enabled: bool = True) -> None:
    """Enable or disable all widgets in a list of widgets."""
    for widget in widgets:
        widget.setEnabled(enabled)


def set_widgets_visible(widgets: list[QWidget], *, visible: bool = True) -> None:
    """Show or hide all widgets in a list of widgets."""
    for widget in widgets:
        widget.setVisible(visible)


def get_layout_widgets(layout: QLayout) -> list[QWidget]:
    """Return all widget that are part of a layout."""
    return [layout.itemAt(i).widget() for i in range(layout.count())]


def delete_layout_widgets(layout: QLayout, except_indeces: list[int] | None = None) -> None:
    """Delete all widgets in a layout without deleting the layout itself.

    Optionally pass list of widget indices to keep.
    """
    # https://stackoverflow.com/a/13103617
    if except_indeces is None:
        except_indeces = []
    for i in reversed(range(layout.count())):
        if i not in except_indeces:
            layout.itemAt(i).widget().deleteLater()
