"""
Startup Manager for QuickAccent.
Allows user to toggle launching QuickAccent on Windows login via HKCU Run registry key.
"""
import os
import sys
import winreg

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "QuickAccent"

def get_launch_command() -> str:
    """Returns the silent background launch command."""
    proj_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    vbs_path = os.path.join(proj_dir, "run_background.vbs")
    return f'wscript.exe "{vbs_path}"'

def is_startup_enabled() -> bool:
    """Check if QuickAccent is currently set to start with Windows."""
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
            if enabled:
                cmd = get_launch_command()
                winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, cmd)
                print(f"[StartupManager] Registered startup command: {cmd}")
            else:
                try:
                    winreg.DeleteValue(key, APP_REG_NAME)
                    print("[StartupManager] Removed startup registry entry.")
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print(f"[StartupManager] Set error: {e}")
        return False
