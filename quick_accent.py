"""
QuickAccent - macOS-style Accent Popup for Windows
Brings the beloved macOS hold-to-accent popup with 1-9 quick selection to Windows,
with first-class out-of-the-box support for the Latvian language (ā, č, ē, ģ, ī, ķ, ļ, ņ, ō, ŗ, š, ū, ž).

Usage:
    python quick_accent.py             # Start background listener & tray icon
    python quick_accent.py --settings  # Start and immediately open settings dialog
"""
import sys
import os
import ctypes
from ctypes import wintypes
import tkinter as tk

# Ensure UTF-8 output encoding for consoles
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from core.config_manager import ConfigManager
from core.overlay_window import AccentOverlay
from core.keyboard_hook import KeyboardManager
from core.tray_icon import TrayIcon
from ui.settings_dialog import SettingsDialog

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

ERROR_ALREADY_EXISTS = 183

def set_high_dpi_awareness():
    """Enable Per-Monitor V2 DPI awareness for sharp rendering on high-res displays."""
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

def acquire_single_instance_mutex():
    """Ensure only one instance of QuickAccent runs at a time."""
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    
    mutex_name = "Local\\QuickAccent_SingleInstance_Mutex"
    h_mutex = kernel32.CreateMutexW(None, True, mutex_name)
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        return None
    return h_mutex

class QuickAccentApp:
    def __init__(self, open_settings_on_start: bool = False):
        self.open_settings_on_start = open_settings_on_start
        
        # Initialize Tkinter root (remains hidden as main event pump)
        self.root = tk.Tk()
        self.root.withdraw()
        
        # Core subsystems
        self.config_manager = ConfigManager()
        self.overlay = AccentOverlay(self.root)
        self.keyboard_manager = KeyboardManager(self.root, self.config_manager, self.overlay)
        self.settings_dialog = SettingsDialog(self.root, self.config_manager, on_change=self._on_settings_changed)
        
        # System tray icon
        self.tray = TrayIcon(
            config_manager=self.config_manager,
            on_open_settings=self._open_settings_from_tray,
            on_exit_app=self.exit_app
        )

    def _open_settings_from_tray(self):
        """Called from tray icon thread: schedule opening dialog on UI thread."""
        self.root.after(0, self.settings_dialog.show)

    def _on_settings_changed(self):
        """Update tray menu when settings change."""
        if self.tray:
            self.tray.refresh()

    def start(self):
        # Start keyboard hook
        self.keyboard_manager.start()
        
        # Start tray icon
        self.tray.start()
        
        if self.open_settings_on_start:
            self.root.after(200, self.settings_dialog.show)

        print("[QuickAccent] Running. Hold any accented key (e.g. a, c, e, g, i, k, l, n, s, u, z) to see popup.")
        print("[QuickAccent] Press numbers 1-9 to insert the corresponding accented character.")
        
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.exit_app()

    def exit_app(self):
        print("[QuickAccent] Exiting application...")
        if self.keyboard_manager:
            self.keyboard_manager.stop()
        if self.tray:
            self.tray.stop()
        self.root.quit()
        self.root.destroy()
        sys.exit(0)

def main():
    set_high_dpi_awareness()
    
    h_mutex = acquire_single_instance_mutex()
    if not h_mutex:
        print("[QuickAccent] An instance of QuickAccent is already running.")
        sys.exit(0)

    open_settings = ("--settings" in sys.argv)
    app = QuickAccentApp(open_settings_on_start=open_settings)
    app.start()

if __name__ == "__main__":
    main()
