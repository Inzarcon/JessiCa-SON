"""Module containing the ProfileSelector widget."""

from __future__ import annotations

from typing import TYPE_CHECKING

from common.logger import get_logger
from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

if TYPE_CHECKING:
    from settings_io.profile_manager import ProfileManager

log = get_logger("App")


class ProfileSelector(QWidget):
    """GUI wrapper widget for the ProfileManager interface."""

    sig_loaded = Signal()
    _profile_mgr: ProfileManager
    _save_new: bool

    def __init__(self, profile_manager: ProfileManager) -> None:
        """Create ProfileSelector that uses given ProfileManager."""
        super().__init__()
        self._profile_mgr = profile_manager

        self.label = QLabel("Profile:")
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.label.setFont(font)

        self.combo = QComboBox()
        self.combo.setMinimumWidth(150)
        self.edit_profile_name = QLineEdit()
        self.edit_profile_name.setPlaceholderText("Set profile name:")
        self.edit_profile_name.setMaximumWidth(200)
        self.btn_save = QPushButton("Save Profile")
        self.btn_save.setMinimumWidth(115)
        self.btn_set_as_default = QPushButton("Set as default")
        self.btn_delete = QPushButton("Delete")

        layout = QHBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.combo)
        layout.addWidget(QLabel("Set Profile Name:"))
        layout.addWidget(self.edit_profile_name)
        layout.addWidget(self.btn_save)
        layout.addWidget(self.btn_set_as_default)
        layout.addWidget(self.btn_delete)
        layout.addStretch()
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.btn_save.clicked.connect(self.save)
        self.btn_set_as_default.clicked.connect(self.set_default)
        self.combo.currentIndexChanged.connect(self.switch)
        self.edit_profile_name.textChanged.connect(self.check_edit_profile_name)
        self.btn_delete.clicked.connect(self.delete_profile)

        profiles = self._profile_mgr.scan()
        default = self._profile_mgr.default_profile_name()
        self.btn_set_as_default.setEnabled(False)
        self.btn_delete.setEnabled(False)

        blocker = QSignalBlocker(self.combo)
        self.combo.addItems(profiles)
        blocker.unblock()

        self.combo.model().sort(0)
        self.edit_profile_name.setText(default)
        self.combo.setCurrentText(default)

    def check_edit_profile_name(self) -> None:
        """React to edit_profile_name change."""
        cur_text = self.edit_profile_name.text()
        if self._profile_mgr.profile_exists(cur_text):
            self.btn_save.setText("Overwrite Profile")
            self._save_new = False
        else:
            self.btn_save.setText("Create new Profile")
            self._save_new = True

    def set_default(self) -> None:
        """Set current profile as new default. Called when btn_set_as_default is clicked."""
        self._profile_mgr.set_as_default()
        self.btn_set_as_default.setEnabled(False)

    def save(self) -> None:
        """Save new profile or overwrite current depending on _save_new. Called when btn_save is clicked."""
        if self._save_new:
            new_profile = self.edit_profile_name.text()

            self._profile_mgr.create_new(new_profile, empty_file=False)

            self.combo.addItem(new_profile)
            self.combo.model().sort(0)
            self.combo.setCurrentText(new_profile)
            self.edit_profile_name.setText(new_profile)

        else:
            self._profile_mgr.check_states_all()

    def switch(self, *, manager_switch: bool = True) -> None:
        """Switch to newly selected profile.

        If manager_switch=False, only the widget switches, but not the internal ProfileManager. Used to avoid recursion
        if the ProfileManager already switched on its own like when deleting a profile.
        """
        profile_name = self.combo.currentText()
        if manager_switch:
            self._profile_mgr.switch(profile_name)

        self.edit_profile_name.setText(profile_name)

        is_default = self._profile_mgr.is_default()
        self.btn_set_as_default.setEnabled(not is_default)
        self.btn_delete.setEnabled(not is_default)

    def delete_profile(self) -> None:
        """Delete the current profile."""
        if self._profile_mgr.is_default():
            log.error("Delete button pressed while on default profile, but should be disabled.")
            return
        self._profile_mgr.delete_profile()

        blocker = QSignalBlocker(self.combo)
        self.combo.removeItem(self.combo.currentIndex())
        self.combo.setCurrentText(self._profile_mgr.profile_name())
        blocker.unblock()
        self.switch(manager_switch=False)  # Manager switches first in this case.

    def _entries(self) -> list[str]:
        # Return the current list of combo box items.
        return [self.combo.itemText(i) for i in range(self.combo.count())]
