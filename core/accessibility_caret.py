"""Isolated UI Automation probe for applications that draw their own caret.

This runs in a short-lived child process so a hung accessibility provider cannot
block the keyboard hook or Tk's UI thread. Only screen coordinates are returned.
"""
import ctypes
import json
import math
import sys
import time


def _rectangle(text_range, last=False):
    values = text_range.GetBoundingRectangles()
    if not values or len(values) % 4:
        return None
    offset = len(values) - 4 if last else 0
    x, y, width, height = values[offset:offset + 4]
    if not all(math.isfinite(v) for v in (x, y, width, height)):
        return None
    if width < 0 or height <= 0:
        return None
    return x, y, width, height


def caret_from_range(text_range):
    """Resolve a collapsed range, including providers that omit empty bounds."""
    rect = _rectangle(text_range)
    if rect:
        return round(rect[0]), round(rect[1]), max(1, round(rect[3]))

    # Prefer the following character, which also handles soft-wrapped line starts.
    # Expanding an empty range can otherwise select an entire word or document.
    following = text_range.Clone()
    if following.MoveEndpointByUnit(1, 0, 1):  # End, Character, forward
        rect = _rectangle(following)
        if rect:
            return round(rect[0]), round(rect[1]), max(1, round(rect[3]))
    preceding = text_range.Clone()
    if preceding.MoveEndpointByUnit(0, 0, -1):  # Start, Character, backward
        rect = _rectangle(preceding, last=True)
        if rect:
            return round(rect[0] + rect[2]), round(rect[1]), max(1, round(rect[3]))
    return None


def find_caret(automation, uia):
    from comtypes import COMError
    element = automation.GetFocusedElement()
    for _ in range(6):
        if not element:
            break
        try:
            unknown = element.GetCurrentPattern(uia.UIA_TextPattern2Id)
            if unknown:
                pattern = unknown.QueryInterface(uia.IUIAutomationTextPattern2)
                active, text_range = pattern.GetCaretRange()
                if active and text_range:
                    caret = caret_from_range(text_range)
                    if caret:
                        return caret
        except (COMError, OSError, ValueError):
            pass
        try:
            unknown = element.GetCurrentPattern(uia.UIA_TextPatternId)
            if unknown:
                pattern = unknown.QueryInterface(uia.IUIAutomationTextPattern)
                ranges = pattern.GetSelection()
                if ranges and ranges.Length:
                    selection = ranges.GetElement(0)
                    # A selection is not a reliable indication of the caret end.
                    if selection.CompareEndpoints(0, selection, 1) == 0:
                        caret = caret_from_range(selection)
                        if caret:
                            return caret
        except (COMError, OSError, ValueError):
            pass
        # Web inputs sometimes expose TextPattern on a focused node's parent.
        element = automation.ControlViewWalker.GetParentElement(element)
    return None


def main():
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = ctypes.c_void_p
    user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    expected_window = int(sys.argv[1])
    if user32.GetForegroundWindow() != expected_window:
        return

    # UI Automation calls use their own MTA, separate from Tk and its callbacks.
    sys.coinit_flags = 0
    from comtypes import COMError
    from comtypes.client import CreateObject, GetModule
    uia = GetModule('UIAutomationCore.dll')
    automation = CreateObject(uia.CUIAutomation, interface=uia.IUIAutomation)
    for delay in (0, .04, .1):
        time.sleep(delay)
        if user32.GetForegroundWindow() != expected_window:
            return
        try:
            caret = find_caret(automation, uia)
        except (COMError, OSError, ValueError):
            caret = None
        if caret and user32.GetForegroundWindow() == expected_window:
            print(json.dumps(caret))
            return


if __name__ == '__main__':
    main()
