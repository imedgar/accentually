"""
Startup Manager for Accentually.
Allows user to toggle launching Accentually on Windows login via HKCU Run registry key.
"""
import os
import sys
import winreg

from core.paths import PROJECT_DIR, is_frozen

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "Accentually"
LEGACY_REG_NAMES = ("QuickAccent",)

def get_launch_command() -> str:
    """Returns the silent background launch command."""
    if is_frozen():
        return f'"{sys.executable}"'
    vbs_path = os.path.join(PROJECT_DIR, "run_background.vbs")
    return f'wscript.exe "{vbs_path}"'

def _delete_value(key, name: str):
    try:
        winreg.DeleteValue(key, name)
    except FileNotFoundError:
        pass

def is_startup_enabled() -> bool:
    """Check if Accentually is currently set to start with Windows."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_REG_NAME)
            return bool(val)
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"[StartupManager] Check error: {e}")
        return False

def set_startup_enabled(enabled: bool) -> bool:
    """Enable or disable starting with Windows."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            # The pre-rename entry points at a path that may no longer exist.
            for legacy in LEGACY_REG_NAMES:
                _delete_value(key, legacy)
            if enabled:
                cmd = get_launch_command()
                winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, cmd)
                print(f"[StartupManager] Registered startup command: {cmd}")
            else:
                _delete_value(key, APP_REG_NAME)
                print("[StartupManager] Removed startup registry entry.")
        return True
    except Exception as e:
        print(f"[StartupManager] Set error: {e}")
        return False
