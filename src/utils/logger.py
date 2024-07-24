"""Module for getting a preconfigured logger with prettier formatting, extra info, color coding, and a Qt Signal."""

import logging
from types import MappingProxyType
from typing import Literal

from colorama import Fore
from PySide6.QtCore import QObject, Signal, Slot


class ColorFormatter(logging.Formatter):
    """Formatter which sets color coding for logger messages.

    Also emits a Qt Signal for each message to be captured in-app as well.
    """

    class _SignalWrapper(QObject):
        # Necessary due to conflicting inherited "emit" method name of Formatter and QObject.
        signal_log = Signal(str)

    fmt_short = "%(levelname)10s %(message)s"  # https://stackoverflow.com/a/60021304
    fmt_details = "%(levelname)10s %(name)s: %(threadName)s %(filename)s, line %(lineno)d, %(funcName)s(): %(message)s"
    colors = MappingProxyType(
        {  # https://stackoverflow.com/a/56944256
            logging.DEBUG: Fore.CYAN,
            logging.INFO: Fore.WHITE,
            logging.WARNING: Fore.LIGHTYELLOW_EX,
            logging.ERROR: Fore.RED,
            logging.CRITICAL: Fore.LIGHTRED_EX,
        },
    )

    def __init__(self) -> None:
        """Initialize the Formatter and Qt Signal."""
        super().__init__()
        self._signal_wrapper = self._SignalWrapper()  # Prevent deletion
        self.signal_log = self._signal_wrapper.signal_log

    def format(self, record: logging.LogRecord) -> str:
        """Return formatted, colored message and also emit it via Qt Signal.

        For the Qt Signal, the emitted string does not contain the special color symbols. Message coloring within the
        GUI is handled separately by the ComposeMessageBox instead. It also does not contain detailed info about logger
        name, module, function, etc. which is not needed for GUI layer.
        """
        formatter_raw = logging.Formatter(self.fmt_short)
        self.signal_log.emit(formatter_raw.format(record))

        color = self.colors.get(record.levelno)
        formatter_colored = logging.Formatter(f"{color}{self.fmt_details}{Fore.RESET}")
        return formatter_colored.format(record)

    def connect_log(self, slot: Slot) -> None:
        """Connect a Qt Slot with the logging Signal."""
        self.signal_log.connect(slot)


def get_logger(
    name: str = __name__,
    start_level: int = logging.INFO,
) -> logging.Logger:
    """Return preconfigured logger with prettier formatting, extra info, color coding, and a Qt Signal."""
    if logging.getLogger(name).hasHandlers():
        return logging.getLogger(name)

    def _fmt_filter(record: logging.LogRecord) -> Literal[True]:
        """Apply additional format filtering with symbols not allowed in format string."""
        # https://stackoverflow.com/a/60021304
        record.levelname = f"[{record.levelname}]"
        record.name = f"{{{record.name}}}"
        return True

    log = logging.getLogger(name)

    formatter = ColorFormatter()
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.addFilter(_fmt_filter)
    log.setLevel(start_level)
    log.addHandler(handler)

    return log
