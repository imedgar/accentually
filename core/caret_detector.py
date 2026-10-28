"""
Caret and Window Position Detector.
Calculates the optimal screen position to display the QuickAccent popup overlay.
Tries caret coordinates first, falling back to mouse or active window geometry.
"""
import ctypes
import subprocess
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

def get_accessible_caret_position():
    """Ask Windows UI Automation for the focused text selection's screen bounds.

    Some applications render their own caret and do not expose a Win32 caret.
    Run this in a worker thread: accessibility providers can be slow or hang.
    """
    script = r'''
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$e = [System.Windows.Automation.AutomationElement]::FocusedElement
if ($null -eq $e) { exit }
$p = $e.GetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern)
if ($null -eq $p) { exit }
$ranges = $p.GetSelection()
if ($ranges.Count -eq 0) { exit }
$rects = $ranges[0].GetBoundingRectangles()
if ($rects.Count -eq 0) {
    $range = $ranges[0].Clone()
    $range.ExpandToEnclosingUnit([System.Windows.Automation.Text.TextUnit]::Character)
    $rects = $range.GetBoundingRectangles()
}
if ($rects.Count -gt 0) {
    $r = $rects[0]
    Write-Output ("{0},{1},{2}" -f [int]$r.X, [int]$r.Y, [int]$r.Height)
}
'''
    try:
        result = subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
            capture_output=True, text=True, timeout=2,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            values = result.stdout.strip().split(',')
            if len(values) == 3:
                return tuple(map(int, values))
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return None

def position_above_caret(x, y, caret_height, width, height):
    _, work_top, _, _ = get_work_area_for_point(x, y)
    popup_y = y - height - 10
    if popup_y < work_top + 10:
        popup_y = y + caret_height + 10
    return clamp_to_screen(x - width // 2, popup_y, width, height)

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
            if user32.ClientToScreen(gui.hwndCaret, ctypes.byref(pt)):
                # Position centered above caret, or below it near the top edge.
                x = pt.x + (caret_w // 2) - (popup_width // 2)
                y = pt.y - popup_height - 10
                _, work_top, _, _ = get_work_area_for_point(pt.x, pt.y)
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
