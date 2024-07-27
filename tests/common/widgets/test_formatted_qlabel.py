"""Test module for FormattedQLabel widget."""

from common.widgets import FormattedQLabel
from PySide6.QtWidgets import QLabel


def test_default(qtbot) -> None:
    """Test formatting of default configuration."""
    lbl = FormattedQLabel("")
    base = QLabel("")

    assert lbl.font().pointSize() == base.font().pointSize()
    assert lbl.font().bold() == base.font().bold()
    assert lbl.font().italic() == base.font().italic()
    assert lbl.styleSheet() == ""


def test_all_set(qtbot) -> None:
    """Test formatting when all parameters are set."""
    lbl = FormattedQLabel("")
    lbl.set_font_size(12)
    lbl.set_bold()
    lbl.set_italic()
    lbl.set_color("red")

    assert lbl.font().bold()
    assert lbl.font().italic()
    assert lbl.font().pointSize() == 12
    assert lbl.styleSheet() == "color: red"


def test_all_overwrite(qtbot) -> None:
    """Test formatting when all parameters are set and then overwritten."""
    lbl = FormattedQLabel("")
    lbl.set_font_size(12)
    lbl.set_bold()
    lbl.set_italic()
    lbl.set_color("red")

    lbl.set_font_size(20)
    lbl.set_bold(bold=False)
    lbl.set_italic(italic=False)
    lbl.set_color("blue")

    assert not lbl.font().bold()
    assert not lbl.font().italic()
    assert lbl.font().pointSize() == 20
    assert lbl.styleSheet() == "color: blue"


def test_all_reset(qtbot) -> None:
    """Test formatting when all parameters are set and then reset."""
    lbl = FormattedQLabel("")
    lbl.set_font_size(12)
    lbl.set_bold()
    lbl.set_italic()
    lbl.set_color("red")

    lbl.set_font_size(9)
    lbl.set_bold(bold=False)
    lbl.set_italic(italic=False)
    lbl.set_color(None)

    base = QLabel("")

    assert lbl.font().pointSize() == base.font().pointSize()
    assert lbl.font().bold() == base.font().bold()
    assert lbl.font().italic() == base.font().italic()
    assert lbl.styleSheet() == ""
