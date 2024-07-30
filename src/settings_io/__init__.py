import sys

from .settings_observer import SettingsObserver, SettingsObserverSavable

if "pytest" not in sys.modules:
    from .main_settings_manager import SETTINGS
    from .profile_manager import PROFILES
