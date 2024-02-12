from compose import ComposeSignalType, MessageType
from PySide6.QtCore import Slot
from PySide6.QtGui import (
    QBrush,
    QColorConstants,
    QFont,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QPlainTextEdit,
    QStackedLayout,
    QWidget,
)


class ComposeMessageBox(QWidget):
    def __init__(self):
        super().__init__()
        self.raw_log = QPlainTextEdit()
        self.raw_log.setReadOnly(True)
        self.set_text_style(self.raw_log)

        self.pretty_log = QPlainTextEdit()
        self.pretty_log.setReadOnly(True)
        self.set_text_style(self.pretty_log)

        self.layout = QStackedLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(self.pretty_log)
        self.layout.addWidget(self.raw_log)

        # Special memory for suggestions
        # TODO: Refactor into set or data class.
        self.seen_unref = 0
        self.seen_sprite_size = False

    def switch(self):
        self.layout.setCurrentIndex(not self.layout.currentIndex())

    def clear(self):
        self.raw_log.clear()
        self.pretty_log.clear()
        self.seen_unref = 0
        self.seen_sprite_size = False

    @Slot(str)
    def message_raw(self, message: str) -> None:
        self.raw_log.appendPlainText(message.replace("\n", ""))
        self.raw_log.moveCursor(QTextCursor.End)

    def message_pretty(self, sig_type, message, args=None, msg_type=None):
        if msg_type:
            if msg_type is MessageType.WARN_SPRITE_UNREF:
                self.seen_unref += 1
            if msg_type is MessageType.ERR_SPRITE_SIZE:
                self.seen_sprite_size = True

        self.pretty_log.appendPlainText("")
        message, args, hinting_styles = self.format_message(
            message, args, msg_type
        )

        if sig_type is ComposeSignalType.WARNING_MESSAGE:
            self.message_formatted_text("[WARNING] ", style_yellow)
        elif sig_type is ComposeSignalType.ERROR_MESSAGE:
            self.message_formatted_text("[ERROR] ", style_red)
        elif sig_type is ComposeSignalType.CRITICAL_MESSAGE:
            self.message_formatted_text("[CRITICAL] ", style_red)
        else:
            self.message_formatted_text("[NOTE] ", style_cyan)

        if not args:
            self.message_formatted_text(message)
            return

        splits = message.split("{}")

        for arg in args:
            if splits:
                self.message_formatted_text(splits.pop(0))
                self.message_formatted_text(arg, hinting_styles.pop(0))

        if splits:  # Text left after last arg
            self.message_formatted_text(splits.pop())

    def message_formatted_text(self, text, format_before=None, format_after=None):
        self.set_text_style(self.pretty_log, format_before)
        self.pretty_log.insertPlainText(str(text))
        self.set_text_style(self.pretty_log, format_after)

    def show_suggestions(self):
        if self.seen_unref:
            self.message_pretty(
                None,
                "There were {} sprites without any JSON reference. If they "
                "are intended to be added automatically, please enable the {}"
                " checkbox above and recompose.",
                (str(self.seen_unref), '"Use All"'),
                "note_unref",
            )
        if self.seen_sprite_size:
            self.message_pretty(
                None,
                "At least one sprite with incorrect pixel size encountered. "
                "This will likely cause bizarre sprite offsets when loaded "
                "in-game.",
                None,
                "note_sprite_size",
            )

    @staticmethod
    def set_text_style(widget, style_dict=None) -> None:
        """
        Shortcut for setting text style of following message strings. Calling
        without style dict resets to default style. Color should
        be a QColorConstant or hex triplet string, e.g. "#FFCC00".
        """
        style_dict = style_default if style_dict is None else style_dict
        char_format = QTextCharFormat()
        font = QFont(style_dict["font_name"])
        font.setStyleHint(style_dict["style_hint"])
        font.setPointSize(style_dict["size"])
        font.setBold(style_dict["bold"])
        char_format.setFont(font)
        char_format.setForeground(QBrush(style_dict["color"]))
        widget.setCurrentCharFormat(char_format)

    @staticmethod
    def format_message(message, args=None, msg_type=None):
        hinting_styles = [style_default]
        if msg_type and msg_type in formats:
            fmt = formats[msg_type]
            if "new_message" in fmt:
                message = fmt["new_message"]
            if "select_args" in fmt:
                args = [args[i] for i in fmt["select_args"]]
            if "hinting_styles" in fmt:
                hinting_styles = fmt["hinting_styles"]
                if len(hinting_styles) < len(args):
                    hinting_styles = [hinting_styles[0]] * len(args)
        else:
            if args:
                hinting_styles = [style_default] * len(args)
        return message, args, list(hinting_styles)


# TODO: Consider loading from file instead of hardcoded -> JSON?
#    -> Would allow user to set preferred colors
style_default = {
    "font_name": "Monospace",
    "style_hint": QFont.StyleHint.SansSerif,
    "size": 10,
    "bold": False,
    "color": QColorConstants.White,
}
# GUI references
style_yellow = dict(style_default)
style_yellow["color"] = "#febb3f"
style_yellow["bold"] = True

# Sheet Type
style_red = dict(style_default)
style_red["color"] = "#ff5762"
style_red["bold"] = True

# IDs, sprites and their properties -> TODO: Split up?
style_cyan = dict(style_default)
style_cyan["color"] = "#19d7e0"
style_cyan["bold"] = True

# Filepaths
style_green = dict(style_default)
style_green["color"] = "#3fbf46"
style_green["bold"] = True


formats = {
    MessageType.CRIT_ERROR_LOADING_JSON: {
        "hinting_styles": (style_green, style_red),
    },
    MessageType.CRIT_COMPOSING_EXCEPT: {
        "hinting_styles": (style_red,),
    },
    MessageType.ERR_SPRITE_SIZE: {
        "hinting_styles": (style_green, *[style_cyan] * 5),
    },
    MessageType.ERR_PNG_NOT_FOUND: {
        "new_message": "Sprite {} was not found and will be ignored. "
        "Referenced in {}.",
        "select_args": (0, 2),
        "hinting_styles": (style_cyan, style_green),
    },
    MessageType.ERR_DUPLICATE_NAME: {
        "hinting_styles": (style_cyan, style_green),
    },
    MessageType.ERR_DUPLICATE_ID: {
        "hinting_styles": (style_cyan, style_green),
    },
    MessageType.ERR_NOT_USED: {
        "hinting_styles": (style_cyan,),
    },
    MessageType.ERR_VIPS: {
        "hinting_styles": (style_green, style_red,),
    },
    MessageType.WARN_SPRITE_UNREF: {
        "new_message": "Ignoring sprite without any JSON reference: [{}] {}.",
        "select_arg": (1, 0),
        "hinting_styles": (style_red, style_cyan),
    },
    MessageType.WARN_NO_FORMATTER: {
        "hinting_styles": (style_green,),
    },
    MessageType.WARN_NOT_MENTIONED: {
        "hinting_styles": (style_cyan,),
    },
    MessageType.WARN_EMPTY_ENTRY: {
        "hinting_styles": (style_green, *[style_cyan] * 2),
    },
    "note_unref": {
        "hinting_styles": (style_cyan, style_yellow),
    },
}
