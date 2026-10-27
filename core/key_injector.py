"""
Low-level keystroke injector using Windows SendInput API.
Replaces the base character with the selected Unicode accented character.
"""
import ctypes
from ctypes import wintypes
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_BACK = 0x08

# Unique magic constant to identify synthetic events from this tool
# (Prevents our WH_KEYBOARD_LL hook from intercepting its own keystrokes)
EXTRA_INFO_MAGIC = 0xACC347

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ('dx', wintypes.LONG),
        ('dy', wintypes.LONG),
        ('mouseData', wintypes.DWORD),
        ('dwFlags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.c_size_t)
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ('wVk', wintypes.WORD),
        ('wScan', wintypes.WORD),
        ('dwFlags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.c_size_t)
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ('uMsg', wintypes.DWORD),
        ('wParamL', wintypes.WORD),
        ('wParamH', wintypes.WORD)
    ]

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [
            ('mi', MOUSEINPUT),
            ('ki', KEYBDINPUT),
            ('hi', HARDWAREINPUT)
        ]
    _anonymous_ = ('_input',)
    _fields_ = [
        ('type', wintypes.DWORD),
        ('_input', _INPUT)
    ]

LPINPUT = ctypes.POINTER(INPUT)
user32.SendInput.argtypes = [wintypes.UINT, LPINPUT, ctypes.c_int]
user32.SendInput.restype = wintypes.UINT

def ensure_desktop_access():
    """Ensure the current thread has access to the input desktop."""
    try:
        desk = user32.OpenInputDesktop(0, False, 0x01FF) # MAXIMUM_ALLOWED
        if desk:
            user32.SetThreadDesktop(desk)
            user32.CloseDesktop(desk)
    except Exception as e:
        pass

def inject_replacement(unicode_char: str) -> bool:
    """
    Atomically sends:
    1. Backspace KeyDown
    2. Backspace KeyUp
    3. Unicode Character KeyDown
    4. Unicode Character KeyUp
    """
    ensure_desktop_access()
    
    # 4 events: 2 for backspace, 2 for unicode char
    inputs = (INPUT * 4)()
    
    # 1. Backspace down
    inputs[0].type = INPUT_KEYBOARD
    inputs[0].ki.wVk = VK_BACK
    inputs[0].ki.wScan = 0
    inputs[0].ki.dwFlags = 0
    inputs[0].ki.time = 0
    inputs[0].ki.dwExtraInfo = EXTRA_INFO_MAGIC

    # 2. Backspace up
    inputs[1].type = INPUT_KEYBOARD
    inputs[1].ki.wVk = VK_BACK
    inputs[1].ki.wScan = 0
    inputs[1].ki.dwFlags = KEYEVENTF_KEYUP
    inputs[1].ki.time = 0
    inputs[1].ki.dwExtraInfo = EXTRA_INFO_MAGIC

    # 3. Unicode char down
    code_point = ord(unicode_char)
    inputs[2].type = INPUT_KEYBOARD
    inputs[2].ki.wVk = 0
    inputs[2].ki.wScan = code_point
    inputs[2].ki.dwFlags = KEYEVENTF_UNICODE
    inputs[2].ki.time = 0
    inputs[2].ki.dwExtraInfo = EXTRA_INFO_MAGIC

    # 4. Unicode char up
    inputs[3].type = INPUT_KEYBOARD
    inputs[3].ki.wVk = 0
    inputs[3].ki.wScan = code_point
    inputs[3].ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
    inputs[3].ki.time = 0
    inputs[3].ki.dwExtraInfo = EXTRA_INFO_MAGIC

    sent = user32.SendInput(4, ctypes.byref(inputs), ctypes.sizeof(INPUT))
    return sent == 4
