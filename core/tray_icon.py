"""
System Tray Icon for Accentually using pystray.
Provides context menu for profile switching, delay adjustment, settings dialog, and clean exit.
"""
import os
import pystray
from PIL import Image
from typing import Callable, Optional
from core.config_manager import ConfigManager
from core.startup_manager import is_startup_enabled, set_startup_enabled

class TrayIcon:
    def __init__(
        self,
        config_manager: ConfigManager,
        on_open_settings: Callable[[], None],
        on_exit_app: Callable[[], None]
    ):
        self.config_manager = config_manager
        self.on_open_settings = on_open_settings
        self.on_exit_app = on_exit_app
        
        ico_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "assets",
            "app_icon.ico"
        )
        self.image = Image.open(ico_path)
        self.icon: Optional[pystray.Icon] = None

    def _build_menu(self) -> pystray.Menu:
        active_prof = self.config_manager.active_profile_name
        current_delay = self.config_manager.hold_delay_ms

        def make_profile_setter(prof_key: str):
            def handler(icon, item):
                self.config_manager.active_profile_name = prof_key
                self.refresh()
            return handler

        def make_delay_setter(ms: int):
            def handler(icon, item):
                self.config_manager.hold_delay_ms = ms
                self.refresh()
            return handler

        def toggle_startup(icon, item):
            currently_on = is_startup_enabled()
            set_startup_enabled(not currently_on)
            self.refresh()

        def handle_settings(icon, item):
            self.on_open_settings()

        def handle_exit(icon, item):
            self.stop()
            self.on_exit_app()

        profiles_menu = pystray.Menu(
            pystray.MenuItem(
                "Latvian + International",
                make_profile_setter("latvian_first"),
                checked=lambda item: self.config_manager.active_profile_name == "latvian_first",
                radio=True
            ),
            pystray.MenuItem(
                "Latvian Exclusive",
                make_profile_setter("latvian_only"),
                checked=lambda item: self.config_manager.active_profile_name == "latvian_only",
                radio=True
            ),
            pystray.MenuItem(
                "Western European",
                make_profile_setter("international"),
                checked=lambda item: self.config_manager.active_profile_name == "international",
                radio=True
            ),
            pystray.MenuItem(
                "Custom Profile",
                make_profile_setter("custom"),
                checked=lambda item: self.config_manager.active_profile_name == "custom",
                radio=True
            )
        )

        delay_menu = pystray.Menu(
            pystray.MenuItem(
                "Fast (250 ms)",
                make_delay_setter(250),
                checked=lambda item: self.config_manager.hold_delay_ms == 250,
                radio=True
            ),
            pystray.MenuItem(
                "Normal (350 ms)",
                make_delay_setter(350),
                checked=lambda item: self.config_manager.hold_delay_ms == 350,
                radio=True
            ),
            pystray.MenuItem(
                "Relaxed (450 ms)",
                make_delay_setter(450),
                checked=lambda item: self.config_manager.hold_delay_ms == 450,
                radio=True
            )
        )

        return pystray.Menu(
            pystray.MenuItem("Accentually (Running)", lambda icon, item: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Profiles", profiles_menu),
            pystray.MenuItem("Hold Delay", delay_menu),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Settings & Custom Keys...", handle_settings, default=True),
            pystray.MenuItem(
                "Start with Windows",
                toggle_startup,
                checked=lambda item: is_startup_enabled()
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit Accentually", handle_exit)
        )

    def start(self):
        """Run the tray icon detached in a background thread."""
        self.icon = pystray.Icon(
            name="Accentually",
            icon=self.image,
            title="Accentually (macOS Accents for Windows)",
            menu=self._build_menu()
        )
        self.icon.run_detached()
        print("[TrayIcon] Tray icon initialized.")

    def refresh(self):
        """Update tray icon menu items."""
        if self.icon:
            self.icon.menu = self._build_menu()
            self.icon.update_menu()

    def stop(self):
        if self.icon:
            self.icon.stop()
            self.icon = None
            print("[TrayIcon] Tray icon stopped.")
