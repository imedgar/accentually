"""
macOS-styled floating accent overlay window for Windows.
Displays available accented variants with 1-9 number badges.
Features non-activating focus preservation, DWM rounded corners, and instant mouse & keyboard selection.
"""
import tkinter as tk
import ctypes
from ctypes import wintypes
from typing import List, Callable, Optional
from core.caret_detector import get_popup_position

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

# Win32 Constants
GWL_EXSTYLE = -20
GWLP_WNDPROC = -4
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WM_MOUSEACTIVATE = 0x0021
MA_NOACTIVATE = 3
SW_HIDE = 0
SW_SHOWNOACTIVATE = 4
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2
DWMWA_USE_IMMERSIVE_DARK_MODE = 20

# 64-bit safe WndProc types
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.CallWindowProcW.restype = ctypes.c_longlong
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongPtrW.restype = ctypes.c_void_p
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
user32.SetWindowLongPtrW.restype = ctypes.c_void_p

class AccentOverlay:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.window = tk.Toplevel(root)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        
        # Color Palette (macOS-inspired Dark Graphite)
        self.bg_color = "#1E1E20"
        self.border_color = "#3A3A3C"
        self.card_bg = "#2C2C2E"
        self.card_selected_bg = "#0A84FF" # Vibrant accent blue
        self.card_hover_bg = "#3A3A3E"
        self.char_fg = "#FFFFFF"
        self.num_fg = "#98989D"
        self.num_selected_fg = "#EBF4FF"
        
        self.window.configure(bg=self.bg_color)
        
        # Geometry constants
        self.card_width = 46
        self.card_height = 58
        self.card_margin = 3
        self.padding = 6
        
        self.options: List[str] = []
        self.selected_index: int = 0
        self.on_select_callback: Optional[Callable[[str], None]] = None
        self.cards: List[dict] = []
        
        # Outer container frame
        self.container = tk.Frame(
            self.window,
            bg=self.bg_color,
            padx=self.padding,
            pady=self.padding,
            highlightthickness=1,
            highlightbackground=self.border_color
        )
        self.container.pack(fill='both', expand=True)
        
        self.window.update_idletasks()
        self._init_win32_attributes()

    def _init_win32_attributes(self):
        """Configure non-activating style, rounded corners, and WndProc intercept."""
        try:
            self.hwnd = user32.GetAncestor(self.window.winfo_id(), 2) # GA_ROOT
            
            # Apply WS_EX_NOACTIVATE so target window stays active
            style = user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(self.hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE | WS_EX_TOPMOST | WS_EX_TOOLWINDOW)
            
            # Subclass WndProc to prevent activation on mouse clicks
            self._old_wndproc = user32.GetWindowLongPtrW(self.hwnd, GWLP_WNDPROC)
            
            def custom_wndproc(hwnd, msg, wparam, lparam):
                if msg == WM_MOUSEACTIVATE:
                    return MA_NOACTIVATE
                return user32.CallWindowProcW(self._old_wndproc, hwnd, msg, wparam, lparam)
            
            self._wndproc_cb = WNDPROC(custom_wndproc)
            user32.SetWindowLongPtrW(self.hwnd, GWLP_WNDPROC, ctypes.cast(self._wndproc_cb, ctypes.c_void_p))
            
            # Windows 11 DWM native rounded corners and dark mode
            pref = ctypes.c_int(DWMWCP_ROUND)
            dwmapi.DwmSetWindowAttribute(self.hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(pref), ctypes.sizeof(pref))
            
            dark = ctypes.c_int(1)
            dwmapi.DwmSetWindowAttribute(self.hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(dark), ctypes.sizeof(dark))
        except Exception as e:
            print(f"[Overlay] Win32 init warning: {e}")

    def show(self, options: List[str], on_select: Callable[[str], None]):
        """Render options and position the popup near caret/cursor."""
        if not options:
            return
            
        self.options = options
        self.selected_index = 0
        self.on_select_callback = on_select
        
        self._rebuild_ui()
        
        # Calculate popup window dimensions
        num_cards = len(options)
        total_width = self.padding * 2 + num_cards * self.card_width + (num_cards - 1) * self.card_margin + 2
        total_height = self.padding * 2 + self.card_height + 2
        
        x, y = get_popup_position(total_width, total_height)
        self.window.geometry(f"{total_width}x{total_height}+{x}+{y}")
        
        # Display window without stealing focus
        user32.ShowWindow(self.hwnd, SW_SHOWNOACTIVATE)
        user32.SetWindowPos(self.hwnd, ctypes.c_void_p(-1), x, y, total_width, total_height, 0x0010 | 0x0040) # HWND_TOPMOST | SWP_NOACTIVATE

    def hide(self):
        """Hide the overlay window."""
        if hasattr(self, 'hwnd') and self.hwnd:
            user32.ShowWindow(self.hwnd, SW_HIDE)
        else:
            self.window.withdraw()
        self.options = []

    def is_visible(self) -> bool:
        return bool(self.options)

    def select_next(self):
        if not self.options:
            return
        self.selected_index = (self.selected_index + 1) % len(self.options)
        self._update_highlight()

    def select_prev(self):
        if not self.options:
            return
        self.selected_index = (self.selected_index - 1) % len(self.options)
        self._update_highlight()

    def select_number(self, num: int) -> bool:
        """Select by 1-based number index (1-9)."""
        idx = num - 1
        if 0 <= idx < len(self.options):
            self.selected_index = idx
            self.confirm_current()
            return True
        return False

    def confirm_current(self):
        """Confirm selection of current highlighted item."""
        if not self.options:
            return
        chosen = self.options[self.selected_index]
        self.hide()
        if self.on_select_callback:
            self.on_select_callback(chosen)

    def _on_card_click(self, index: int):
        self.selected_index = index
        self.confirm_current()

    def _on_card_hover(self, index: int):
        self.selected_index = index
        self._update_highlight()

    def _rebuild_ui(self):
        # Clear existing card widgets
        for widget in self.container.winfo_children():
            widget.destroy()
        self.cards.clear()
        
        for idx, char in enumerate(self.options):
            num_str = str(idx + 1) if idx < 9 else ""
            is_sel = (idx == self.selected_index)
            
            bg = self.card_selected_bg if is_sel else self.card_bg
            num_color = self.num_selected_fg if is_sel else self.num_fg
            
            card = tk.Frame(
                self.container,
                bg=bg,
                width=self.card_width,
                height=self.card_height,
                cursor="hand2"
            )
            card.pack_propagate(False)
            card.pack(side="left", padx=self.card_margin // 2)
            
            # Character label
            lbl_char = tk.Label(
                card,
                text=char,
                font=("Segoe UI", 16, "bold"),
                bg=bg,
                fg=self.char_fg,
                cursor="hand2"
            )
            lbl_char.pack(expand=True, fill="both", pady=(2, 0))
            
            # Number label (1-9)
            lbl_num = tk.Label(
                card,
                text=num_str,
                font=("Segoe UI", 8),
                bg=bg,
                fg=num_color,
                cursor="hand2"
            )
            lbl_num.pack(side="bottom", pady=(0, 3))
            
            # Bind mouse clicks and hover
            def make_click_handler(i):
                return lambda e: self._on_card_click(i)
            def make_hover_handler(i):
                return lambda e: self._on_card_hover(i)
                
            for w in (card, lbl_char, lbl_num):
                w.bind("<Button-1>", make_click_handler(idx))
                w.bind("<Enter>", make_hover_handler(idx))
                
            self.cards.append({
                "frame": card,
                "lbl_char": lbl_char,
                "lbl_num": lbl_num
            })

    def _update_highlight(self):
        for idx, card_dict in enumerate(self.cards):
            is_sel = (idx == self.selected_index)
            bg = self.card_selected_bg if is_sel else self.card_bg
            num_color = self.num_selected_fg if is_sel else self.num_fg
            
            card_dict["frame"].configure(bg=bg)
            card_dict["lbl_char"].configure(bg=bg)
            card_dict["lbl_num"].configure(bg=bg, fg=num_color)
