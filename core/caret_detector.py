"""
Caret and Window Position Detector.
Calculates the optimal screen position to display the QuickAccent popup overlay.
Tries caret coordinates first, falling back to mouse or active window geometry.
"""
import ctypes
import json
import os
import subprocess
import sys
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

# Window and monitor handles are pointer-sized on 64-bit Windows.
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetGUIThreadInfo.argtypes = [wintypes.DWORD, ctypes.POINTER(GUITHREADINFO)]
user32.GetGUIThreadInfo.restype = wintypes.BOOL
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.ClientToScreen.restype = wintypes.BOOL
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
user32.MonitorFromPoint.restype = wintypes.HANDLE
user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MONITORINFO)]
user32.GetMonitorInfoW.restype = wintypes.BOOL
user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
user32.MonitorFromWindow.restype = wintypes.HANDLE
user32.IsZoomed.argtypes = [wintypes.HWND]
user32.IsZoomed.restype = wintypes.BOOL
user32.GetDesktopWindow.restype = wintypes.HWND
user32.GetShellWindow.restype = wintypes.HWND

def is_foreground_fullscreen():
    """Detect a non-maximized window covering its monitor, including borderless games."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd or hwnd in (user32.GetDesktopWindow(), user32.GetShellWindow()) or user32.IsZoomed(hwnd):
        return False
    rect = RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return False
    monitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(info)
    if not monitor or not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        return False
    screen = info.rcMonitor
    return (rect.left <= screen.left and rect.top <= screen.top and
            rect.right >= screen.right and rect.bottom >= screen.bottom)

def caret_belongs_to_window(caret, hwnd):
    if not caret or not hwnd:
        return False
    x, y, height = caret
    rect = RECT()
    return (height > 0 and user32.GetWindowRect(hwnd, ctypes.byref(rect)) and
            rect.left <= x <= rect.right and rect.top <= y < rect.bottom)


def get_accessible_caret_position(hwnd=None):
    """Query the active caret in a bounded child process, off the UI thread."""
    hwnd = hwnd or user32.GetForegroundWindow()
    if not hwnd:
        return None
    try:
        result = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), 'accessibility_caret.py'), str(hwnd)],
            capture_output=True, text=True, timeout=2,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0 and user32.GetForegroundWindow() == hwnd:
            values = json.loads(result.stdout)
            if (isinstance(values, list) and len(values) == 3 and
                    all(type(value) is int for value in values) and
                    caret_belongs_to_window(values, hwnd)):
                return tuple(values)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return None


def get_native_caret_position(hwnd=None):
    hwnd = hwnd or user32.GetForegroundWindow()
    if not hwnd:
        return None
    tid = user32.GetWindowThreadProcessId(hwnd, None)
    if not tid:
        return None
    gui = GUITHREADINFO()
    gui.cbSize = ctypes.sizeof(gui)
    if user32.GetGUIThreadInfo(tid, ctypes.byref(gui)) and gui.hwndCaret:
        width = gui.rcCaret.right - gui.rcCaret.left
        height = gui.rcCaret.bottom - gui.rcCaret.top
        if height > 0:
            point = wintypes.POINT(gui.rcCaret.left, gui.rcCaret.top)
            if user32.ClientToScreen(gui.hwndCaret, ctypes.byref(point)):
                caret = point.x + max(0, width) // 2, point.y, height
                if caret_belongs_to_window(caret, hwnd):
                    return caret
    return None

def position_above_caret(x, y, caret_height, width, height):
    work_area = get_work_area_for_point(x, y)
    _, work_top, _, _ = work_area
    popup_y = y - height - 10
    if popup_y < work_top + 10:
        popup_y = y + caret_height + 10
    return clamp_to_screen(x - width // 2, popup_y, width, height, work_area)

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

def clamp_to_screen(x: int, y: int, width: int, height: int, work_area=None) -> Tuple[int, int]:
    work_left, work_top, work_right, work_bottom = work_area or get_work_area_for_point(x, y)
    margin = 8
    clamped_x = max(work_left + margin, min(x, work_right - width - margin))
    clamped_y = max(work_top + margin, min(y, work_bottom - height - margin))
    return (int(clamped_x), int(clamped_y))

def get_popup_position(popup_width: int, popup_height: int, caret=None) -> Tuple[int, int]:
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
    caret = caret or get_native_caret_position(hwnd_fg)
    if caret:
        return position_above_caret(*caret, popup_width, popup_height)

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
