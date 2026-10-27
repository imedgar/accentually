"""
Caret and Window Position Detector.
Calculates the optimal screen position to display the QuickAccent popup overlay.
Tries caret coordinates first, falling back to mouse or active window geometry.
"""
import ctypes
from ctypes import wintypes
from typing import Tuple

user32 = ctypes.windll.user32

class RECT(ctypes.Structure):
    _fields_ = [
        ('left', wintypes.LONG),
        ('top', wintypes.LONG),
        ('right', wintypes.LONG),
        ('bottom', wintypes.LONG)
    ]

class GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('flags', wintypes.DWORD),
        ('hwndActive', wintypes.HWND),
        ('hwndFocus', wintypes.HWND),
        ('hwndCapture', wintypes.HWND),
        ('hwndMenuOwner', wintypes.HWND),
        ('hwndMoveSize', wintypes.HWND),
        ('hwndCaret', wintypes.HWND),
        ('rcCaret', RECT)
    ]

class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('rcMonitor', RECT),
        ('rcWork', RECT),
        ('dwFlags', wintypes.DWORD)
    ]

MONITOR_DEFAULTTONEAREST = 2

def get_work_area_for_point(x: int, y: int) -> Tuple[int, int, int, int]:
    """Returns (left, top, right, bottom) of the display work area."""
    pt = wintypes.POINT(x, y)
    hmon = user32.MonitorFromPoint(pt, MONITOR_DEFAULTTONEAREST)
    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
        return (mi.rcWork.left, mi.rcWork.top, mi.rcWork.right, mi.rcWork.bottom)
    # Fallback to primary screen metrics
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    return (0, 0, w, h)

def clamp_to_screen(x: int, y: int, width: int, height: int) -> Tuple[int, int]:
    work_left, work_top, work_right, work_bottom = get_work_area_for_point(x, y)
    margin = 8
    clamped_x = max(work_left + margin, min(x, work_right - width - margin))
    clamped_y = max(work_top + margin, min(y, work_bottom - height - margin))
    return (int(clamped_x), int(clamped_y))

def get_popup_position(popup_width: int, popup_height: int) -> Tuple[int, int]:
    """
    Calculates the screen (x, y) for the popup.
    Priority 1: Native caret position (right above the character).
    Priority 2: Mouse cursor position (if inside foreground window).
    Priority 3: Horizontal center of the active foreground window.
    """
    hwnd_fg = user32.GetForegroundWindow()
    if not hwnd_fg:
        # Fallback to mouse cursor
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        return clamp_to_screen(pt.x - (popup_width // 2), pt.y - popup_height - 12, popup_width, popup_height)

    # 1. Try GetGUIThreadInfo caret
    tid = user32.GetWindowThreadProcessId(hwnd_fg, None)
    gui = GUITHREADINFO()
    gui.cbSize = ctypes.sizeof(GUITHREADINFO)
    
    if user32.GetGUIThreadInfo(tid, ctypes.byref(gui)) and gui.hwndCaret:
        caret_w = gui.rcCaret.right - gui.rcCaret.left
        caret_h = gui.rcCaret.bottom - gui.rcCaret.top
        
        # Check if caret rect is non-zero
        if caret_w > 0 or caret_h > 0:
            pt = wintypes.POINT(gui.rcCaret.left, gui.rcCaret.top)
            user32.ClientToScreen(gui.hwndCaret, ctypes.byref(pt))
            
            # Position centered above caret
            x = pt.x + (caret_w // 2) - (popup_width // 2)
            y = pt.y - popup_height - 10
            
            # If too close to top of screen, position below caret
            work_left, work_top, work_right, work_bottom = get_work_area_for_point(pt.x, pt.y)
            if y < work_top + 10:
                y = pt.y + caret_h + 10
                
            return clamp_to_screen(x, y, popup_width, popup_height)

    # 2. Try mouse cursor position if inside foreground window
    pt_cursor = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt_cursor))
    rect_fg = RECT()
    user32.GetWindowRect(hwnd_fg, ctypes.byref(rect_fg))
    
    if (rect_fg.left <= pt_cursor.x <= rect_fg.right and
        rect_fg.top <= pt_cursor.y <= rect_fg.bottom):
        x = pt_cursor.x - (popup_width // 2)
        y = pt_cursor.y - popup_height - 15
        work_left, work_top, _, _ = get_work_area_for_point(pt_cursor.x, pt_cursor.y)
        if y < work_top + 10:
            y = pt_cursor.y + 25
        return clamp_to_screen(x, y, popup_width, popup_height)

    # 3. Fallback: Center-top of foreground window
    win_w = rect_fg.right - rect_fg.left
    x = rect_fg.left + (win_w - popup_width) // 2
    y = rect_fg.top + 80
    return clamp_to_screen(x, y, popup_width, popup_height)
