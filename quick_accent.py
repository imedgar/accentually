"""
Accentually - macOS-style Accent Popup for Windows
Brings the beloved macOS hold-to-accent popup with 1-9 quick selection to Windows,
with first-class out-of-the-box support for the Latvian language (ā, č, ē, ģ, ī, ķ, ļ, ņ, ō, ŗ, š, ū, ž).

Usage:
    python quick_accent.py             # Start background listener & tray icon
    python quick_accent.py --settings  # Start and immediately open settings dialog
"""
import sys

if len(sys.argv) == 3 and sys.argv[1] == "--caret":
    # Frozen builds run the UI Automation caret probe as this same exe (see caret_detector).
    from core.accessibility_caret import main as _caret_probe
    sys.argv = [sys.argv[0], sys.argv[2]]
    _caret_probe()
    sys.exit(0)

import os
import time
import threading
import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import messagebox

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
from core import updater
from core.paths import is_frozen, resource_path
from core.version import __version__

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

ERROR_ALREADY_EXISTS = 183
UPDATE_INTERVAL_S = 24 * 3600

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
    """Ensure only one instance of Accentually runs at a time."""
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    
    mutex_name = "Local\\QuickAccent_SingleInstance_Mutex"
    h_mutex = kernel32.CreateMutexW(None, True, mutex_name)
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        return None
    return h_mutex

class AccentuallyApp:
    def __init__(self, open_settings_on_start: bool = False):
        self.open_settings_on_start = open_settings_on_start
        self.pending_update = None
        
        # Initialize Tkinter root (remains hidden as main event pump)
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.iconbitmap(resource_path("assets", "app_icon.ico"))
        
        # Core subsystems
        self.config_manager = ConfigManager()
        self.overlay = AccentOverlay(self.root)
        self.keyboard_manager = KeyboardManager(self.root, self.config_manager, self.overlay)
        self.settings_dialog = SettingsDialog(self.root, self.config_manager, on_change=self._on_settings_changed)
        
        # System tray icon
        self.tray = TrayIcon(
            config_manager=self.config_manager,
            on_open_settings=self._open_settings_from_tray,
            on_exit_app=lambda: self.root.after(0, self.exit_app),
            on_check_updates=lambda: self.root.after(0, lambda: self.check_for_updates(manual=True)),
            on_install_update=lambda: self.root.after(0, self.install_update),
            get_pending_update=lambda: self.pending_update.version if self.pending_update else None,
        )

    # ---- Updates -------------------------------------------------------
    def _schedule_auto_update_check(self):
        if self.config_manager.check_updates and time.time() - self.config_manager.last_update_check > UPDATE_INTERVAL_S:
            self.root.after(30_000, lambda: self.check_for_updates(manual=False))
        # Re-evaluate daily so long-running sessions also pick up releases.
        self.root.after(UPDATE_INTERVAL_S * 1000, self._schedule_auto_update_check)

    def check_for_updates(self, manual: bool):
        def worker():
            try:
                info, error = updater.fetch_latest(), None
            except updater.UpdateError as exc:
                info, error = None, str(exc)
            self.root.after(0, lambda: self._on_update_checked(info, error, manual))
        threading.Thread(target=worker, daemon=True).start()

    def _on_update_checked(self, info, error, manual: bool):
        if error:
            if manual:
                messagebox.showerror("Accentually", "Update check failed.\n\n" + error)
            return
        self.config_manager.last_update_check = time.time()
        if info and updater.is_newer(info.version):
            self.pending_update = info
            self.tray.refresh()
            if manual:
                self.install_update()
            elif self.tray.icon:
                self.tray.icon.notify(f"Version {info.version} is available. Use the tray menu to install it.", "Accentually update")
        elif manual:
            messagebox.showinfo("Accentually", f"You're up to date (version {__version__}).")

    def install_update(self):
        info = self.pending_update
        if not info:
            return
        if not is_frozen():
            messagebox.showinfo("Accentually", f"Version {info.version} is available.\n"
                                "Running from source: update with git pull.")
            return
        question = (f"Install Accentually {info.version} now? (you have {__version__})\n\n"
                    f"{info.notes[:600]}\n\nThe app will restart.")
        if not messagebox.askyesno("Accentually", question):
            return

        def worker():
            try:
                path = updater.download(info)
            except updater.UpdateError as exc:
                message = "Update failed.\n\n" + str(exc)
                self.root.after(0, lambda: messagebox.showerror("Accentually", message))
                return
            self.root.after(0, lambda: self._launch_update(path))
        threading.Thread(target=worker, daemon=True).start()

    def _launch_update(self, installer_path: str):
        updater.launch_installer(installer_path)
        if self.keyboard_manager:
            self.keyboard_manager.stop()
        if self.tray:
            self.tray.stop()
        os._exit(0)  # Release the single-instance mutex so the installer can replace the files.

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
        self._schedule_auto_update_check()
        
        if self.open_settings_on_start:
            self.root.after(200, self.settings_dialog.show)

        print("[Accentually] Running. Hold any accented key (e.g. a, c, e, g, i, k, l, n, s, u, z) to see popup.")
        print("[Accentually] Press numbers 1-9 to insert the corresponding accented character.")
        
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.exit_app()

    def exit_app(self):
        print("[Accentually] Exiting application...")
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
        print("[Accentually] An instance of Accentually is already running.")
        sys.exit(0)

    open_settings = ("--settings" in sys.argv)
    app = AccentuallyApp(open_settings_on_start=open_settings)
    app.start()

if __name__ == "__main__":
    main()
