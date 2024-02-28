"""
Module for getting a preconfigured default logger with prettier formatting,
color coding, and a Qt Signal.
"""

import logging

from colorama import Fore
from PySide6.QtCore import QObject, Signal, Slot


class ColorFormatter(logging.Formatter):
    """
    logging.StreamHandler which sets color coding for logger messages.
    Also emits a Qt Signal for each message to be captured in-app as well.
    """

    class _SignalWrapper(QObject):
        # Necessary due to conflicting inherited "emit" method name between
        # StreamHandler and QObject.
        signal_log = Signal(str)

    def __init__(self):
        super().__init__()
        self._signal_wrapper = self._SignalWrapper()  # Prevent deletion
        self.signal_log = self._signal_wrapper.signal_log

        # https://stackoverflow.com/a/56944256
        self.fmt = "%(levelname)10s %(message)s"
        self.colors = {
            logging.DEBUG: Fore.CYAN,
            logging.INFO: Fore.WHITE,
            logging.WARNING: Fore.LIGHTYELLOW_EX,
            logging.ERROR: Fore.RED,
            logging.CRITICAL: Fore.LIGHTRED_EX,
        }

    def format(self, record):
        """Apply color coding and write record to stream."""
        color = self.colors.get(record.levelno)
        formatter = logging.Formatter(color + self.fmt + Fore.RESET)
        result = formatter.format(record)
        self.signal_log.emit(result[5:-4])  # Remove special color characters
        return result

    def connect_log(self, slot: Slot):
        """Connect a Qt Slot with the logging Signal."""
        self.signal_log.connect(slot)


def get_logger(
    name: str = __name__,
    start_level: int = logging.DEBUG,
) -> logging.Logger:
    """
    TODO: Setting log level (ColorHandler needs to be set too)
    Returns default logger with prettier formatting, color coding, and a Qt
    Signal.
    """
    if logging.getLogger(name).hasHandlers():
        return logging.getLogger(name)

    # https://stackoverflow.com/a/60021304
    def fmt_filter(record):
        record.levelname = f"[{record.levelname}]"
        record.funcName = f"[{record.funcName}]"
        return True

    log = logging.getLogger(name)

    formatter = ColorFormatter()
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.addFilter(fmt_filter)
    log.setLevel(start_level)
    log.addHandler(handler)

    return log
