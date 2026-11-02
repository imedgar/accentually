"""Locations of bundled resources and per-user data, for source and frozen (PyInstaller) runs."""
import os
import sys

APP_NAME = "Accentually"
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_path(*parts: str) -> str:
    """Path to a bundled read-only resource (e.g. assets/app_icon.ico)."""
    base = getattr(sys, "_MEIPASS", PROJECT_DIR)
    return os.path.join(base, *parts)


def user_data_dir() -> str:
    """Writable per-user folder; the install directory may be read-only."""
    path = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def default_config_path() -> str:
    # Running from source keeps using the repo's config.json; installs use %APPDATA%.
    if is_frozen():
        return os.path.join(user_data_dir(), "config.json")
    return os.path.join(PROJECT_DIR, "config.json")
