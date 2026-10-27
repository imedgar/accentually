"""
Low-Level Keyboard Hook (WH_KEYBOARD_LL) and Press-and-Hold state machine.
Replicates macOS accent menu:
- Zero lag for normal typing.
- Blocks repeat while holding.
- Displays popup overlay after hold delay.
- Intercepts 1-9, Arrow keys, Enter, Space, and Escape.
"""
import ctypes
from ctypes import wintypes
import threading
import time
from typing import Optional, Callable
from core.key_injector import EXTRA_INFO_MAGIC, inject_replacement
from core.config_manager import ConfigManager
from core.overlay_window import AccentOverlay

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12 # Alt
VK_CAPITAL = 0x14 # Caps Lock
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_RETURN = 0x0D
VK_BACK = 0x08
VK_LEFT = 0x25
VK_RIGHT = 0x27
VK_LWIN = 0x5B
VK_RWIN = 0x5C

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ('vkCode', wintypes.DWORD),
        ('scanCode', wintypes.DWORD),
        ('flags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.c_size_t)
    ]

HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

class KeyboardManager:
    def __init__(self, root, config_manager: ConfigManager, overlay: AccentOverlay):
        self.root = root
        self.config_manager = config_manager
        self.overlay = overlay
        
        self.hook = None
        self._hook_proc_ref = None # Prevent garbage collection
        
        # State tracking
        self.currently_held_vk: Optional[int] = None
        self.hold_timer: Optional[threading.Timer] = None
        self.is_popup_active: bool = False
        self.active_base_char: Optional[str] = None
        self.active_is_upper: bool = False

    def start(self):
        """Install global low-level keyboard hook."""
        self._hook_proc_ref = HOOKPROC(self._hook_callback)
        # In Windows WH_KEYBOARD_LL, hMod can be NULL (0)
        self.hook = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self._hook_proc_ref,
            0,
            0
        )
        if not self.hook:
            err = kernel32.GetLastError()
            print(f"[KeyboardManager] Failed to set hook: error {err}")
        else:
            print("[KeyboardManager] Global keyboard hook active.")

    def stop(self):
        """Unhook global keyboard hook."""
        self._cancel_timer()
        if self.hook:
            user32.UnhookWindowsHookEx(self.hook)
            self.hook = None
            print("[KeyboardManager] Hook uninstalled.")

    def _cancel_timer(self):
        if self.hold_timer:
            self.hold_timer.cancel()
            self.hold_timer = None

    def _is_modifier_down(self) -> bool:
        """Check if Ctrl, Alt, or Win keys are pressed."""
        return (
            (user32.GetKeyState(VK_CONTROL) & 0x8000) != 0 or
            (user32.GetKeyState(VK_MENU) & 0x8000) != 0 or
            (user32.GetKeyState(VK_LWIN) & 0x8000) != 0 or
            (user32.GetKeyState(VK_RWIN) & 0x8000) != 0
        )

    def _get_is_upper(self) -> bool:
        shift_down = (user32.GetKeyState(VK_SHIFT) & 0x8000) != 0
        caps_on = (user32.GetKeyState(VK_CAPITAL) & 0x0001) != 0
        return (shift_down ^ caps_on)

    def _vk_to_char(self, vkCode: int) -> Optional[str]:
        """Convert a virtual key code to a base character (lowercase)."""
        # A-Z
        if 0x41 <= vkCode <= 0x5A:
            return chr(vkCode).lower()
        # Digits 0-9
        if 0x30 <= vkCode <= 0x39:
            return chr(vkCode)
        return None

    def _on_hold_timeout(self, base_char: str, is_upper: bool):
        """Triggered on background timer when a key is held past threshold."""
        # Schedule UI update on main thread
        self.root.after(0, self._show_overlay_on_ui_thread, base_char, is_upper)

    def _show_overlay_on_ui_thread(self, base_char: str, is_upper: bool):
        options = self.config_manager.get_mappings_for_key(base_char, is_upper)
        if not options:
            return
            
        self.is_popup_active = True
        self.active_base_char = base_char
        self.active_is_upper = is_upper
        
        def on_char_selected(chosen_char: str):
            self.is_popup_active = False
            self.active_base_char = None
            self.currently_held_vk = None
            inject_replacement(chosen_char)

        self.overlay.show(options, on_char_selected)

    def _dismiss_overlay(self):
        self.is_popup_active = False
        self.active_base_char = None
        self.overlay.hide()

    def _hook_callback(self, nCode: int, wParam: wintypes.WPARAM, lParam: wintypes.LPARAM) -> int:
        if nCode < 0:
            return user32.CallNextHookEx(None, nCode, wParam, lParam)

        kbd = KBDLLHOOKSTRUCT.from_address(lParam)
        
        # 1. Ignore synthetic events generated by our own SendInput
        if kbd.dwExtraInfo == EXTRA_INFO_MAGIC or (kbd.flags & 0x0010):
            return user32.CallNextHookEx(None, nCode, wParam, lParam)

        is_key_down = (wParam == WM_KEYDOWN or wParam == WM_SYSKEYDOWN)
        is_key_up = (wParam == WM_KEYUP or wParam == WM_SYSKEYUP)
        vk = kbd.vkCode

        # ---------------------------------------------------------
        # STATE A: Accent Popup is CURRENTLY ACTIVE
        # ---------------------------------------------------------
        if self.is_popup_active:
            if is_key_down:
                # 1. Check numbers 1-9 (top row or numpad)
                num = None
                if 0x31 <= vk <= 0x39: # Top row '1'-'9'
                    num = vk - 0x30
                elif 0x61 <= vk <= 0x69: # Numpad '1'-'9'
                    num = vk - 0x60
                    
                if num is not None:
                    # Select option by number!
                    if self.overlay.select_number(num):
                        self.is_popup_active = False
                        self.currently_held_vk = None
                        return 1 # Suppress digit

                # 2. Navigation: Left / Right arrow keys
                if vk == VK_LEFT:
                    self.overlay.select_prev()
                    return 1
                if vk == VK_RIGHT:
                    self.overlay.select_next()
                    return 1

                # 3. Confirmation: Space or Enter
                if vk == VK_SPACE or vk == VK_RETURN:
                    self.overlay.confirm_current()
                    self.is_popup_active = False
                    self.currently_held_vk = None
                    return 1

                # 4. Cancellation: Escape
                if vk == VK_ESCAPE:
                    self._dismiss_overlay()
                    return 1

                # 5. Backspace: dismiss popup and delete the character
                if vk == VK_BACK:
                    self._dismiss_overlay()
                    return user32.CallNextHookEx(None, nCode, wParam, lParam)

                # 6. Any other key: dismiss popup and let normal typing proceed
                self._dismiss_overlay()
                return user32.CallNextHookEx(None, nCode, wParam, lParam)

            elif is_key_up:
                # When releasing the held key while popup is open:
                # Keep the popup open so user can comfortably tap 1-9!
                return user32.CallNextHookEx(None, nCode, wParam, lParam)

        # ---------------------------------------------------------
        # STATE B: Normal typing (Popup is NOT active)
        # ---------------------------------------------------------
        if is_key_down:
            # If modifier keys (Ctrl/Alt/Win) are held, ignore (preserve shortcuts)
            if self._is_modifier_down():
                self._cancel_timer()
                self.currently_held_vk = None
                return user32.CallNextHookEx(None, nCode, wParam, lParam)

            base_char = self._vk_to_char(vk)
            if base_char and base_char in self.config_manager.get_all_active_base_keys():
                if self.currently_held_vk == vk:
                    # Hardware key repeat while holding!
                    # Suppress repeat so document isn't flooded with letters
                    return 1
                else:
                    # First keydown for this character
                    self._cancel_timer()
                    self.currently_held_vk = vk
                    is_upper = self._get_is_upper()
                    
                    # Start hold timer (e.g. 350 ms)
                    delay_sec = self.config_manager.hold_delay_ms / 1000.0
                    self.hold_timer = threading.Timer(
                        delay_sec,
                        self._on_hold_timeout,
                        args=[base_char, is_upper]
                    )
                    self.hold_timer.daemon = True
                    self.hold_timer.start()
                    
                    # Pass initial keydown through immediately (zero latency typing!)
                    return user32.CallNextHookEx(None, nCode, wParam, lParam)
            else:
                # Key is not in mapped accents list
                self._cancel_timer()
                self.currently_held_vk = None
                return user32.CallNextHookEx(None, nCode, wParam, lParam)

        elif is_key_up:
            if vk == self.currently_held_vk:
                # User released key before hold delay: normal quick tap!
                self._cancel_timer()
                self.currently_held_vk = None

            return user32.CallNextHookEx(None, nCode, wParam, lParam)

        return user32.CallNextHookEx(None, nCode, wParam, lParam)
