"""Module containing FormattedQLabel component."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel

if TYPE_CHECKING:
    from collections.abc import Callable


def _apply_font(func: Callable) -> Callable:
    def wrapper(self: FormattedQLabel, *args: tuple, **kwargs: dict[str, dict]) -> None:
        func(self, *args, **kwargs)
        self.setFont(self._font)

    return wrapper


class FormattedQLabel(QLabel):
    """QLabel with built-in QFont and coloring."""

    _font: QFont = QFont()  # type: ignore[assignment]

    def __init__(
        self,
        text: str,
        *,
        font_size: int | None = None,
        bold: bool = False,
        italic: bool = False,
        color: str | None = None,
    ) -> None:
        """Create Formatted QLabel and set initial text format.

        If passing color, it should be a valid color name ("red") or a 6-digit hexcode ("#FF0000").
        """
        super().__init__(text=text)

        if font_size is not None:
            self.set_font_size(font_size)

        self.set_bold(bold=bold)
        self.set_italic(italic=italic)

        if color is not None:
            self.set_color(color)

    @_apply_font
    def set_font_size(self, font_size: int) -> None:
        """Set text font size."""
        self._font.setPointSize(font_size)

    @_apply_font
    def set_bold(self, *, bold: bool = True) -> None:
        """Set text font bold. Alternatively, remove bold formatting by passing bold=False."""
        self._font.setBold(bold)

    @_apply_font
    def set_italic(self, *, italic: bool = True) -> None:
        """Set text font italic. Alternatively, remove italic formatting by passing italic=False."""
        self._font.setItalic(italic)

    def set_color(self, color: str | None = None) -> None:
        """Set text color.

        Input color should be a valid color name ("red") or a 6-digit hexcode ("#FF0000"). If color=None, remove
        specific coloring and go back to default color.
        """
        if color is None:
            self.setStyleSheet("")
        else:
            self.setStyleSheet(f"color: {color}")
