import ctypes
import time
import random
import math
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
KEYEVENTF_KEYUP = 0x0002
VK_LBUTTON = 0x01


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", INPUT_UNION)]


def _send_input(*inputs):
    n = len(inputs)
    arr = (INPUT * n)(*inputs)
    user32.SendInput(n, arr, ctypes.sizeof(INPUT))


def _make_mouse_input(dx, dy, flags):
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.union.mi.dx = dx
    inp.union.mi.dy = dy
    inp.union.mi.mouseData = 0
    inp.union.mi.dwFlags = flags
    inp.union.mi.time = 0
    inp.union.mi.dwExtraInfo = None
    return inp


def _ease_in_out(t: float) -> float:
    if t < 0.5:
        return 2 * t * t
    return -1 + (4 - 2 * t) * t


def move_mouse_to(x: int, y: int, duration_ms: int = 0):
    if duration_ms <= 0:
        user32.SetCursorPos(x, y)
        return

    start_x = ctypes.c_long()
    start_y = ctypes.c_long()
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    start_x = pt.x
    start_y = pt.y

    steps = max(2, duration_ms // 5)
    for i in range(steps + 1):
        t = i / steps
        eased = _ease_in_out(t)
        cur_x = int(start_x + (x - start_x) * eased)
        cur_y = int(start_y + (y - start_y) * eased)
        user32.SetCursorPos(cur_x, cur_y)
        time.sleep(0.005)


def move_mouse_to_absolute(x: int, y: int, duration_ms: int = 0):
    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1)
    abs_x = int(x * 65535 / screen_w)
    abs_y = int(y * 65535 / screen_h)

    if duration_ms <= 0:
        inp = _make_mouse_input(abs_x, abs_y, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE)
        _send_input(inp)
        return

    start_x = ctypes.c_long()
    start_y = ctypes.c_long()
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    start_x = pt.x
    start_y = pt.y

    steps = max(2, duration_ms // 5)
    for i in range(steps + 1):
        t = i / steps
        eased = _ease_in_out(t)
        cur_x = int(start_x + (x - start_x) * eased)
        cur_y = int(start_y + (y - start_y) * eased)
        abs_x = int(cur_x * 65535 / screen_w)
        abs_y = int(cur_y * 65535 / screen_h)
        inp = _make_mouse_input(abs_x, abs_y, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE)
        _send_input(inp)
        time.sleep(0.005)


def click_at(x: int, y: int, click_type: str = "single"):
    move_mouse_to(x, y, 0)
    time.sleep(random.uniform(0.01, 0.03))

    down = _make_mouse_input(0, 0, MOUSEEVENTF_LEFTDOWN)
    up = _make_mouse_input(0, 0, MOUSEEVENTF_LEFTUP)
    _send_input(down)
    time.sleep(random.uniform(0.005, 0.03))
    _send_input(up)

    if click_type == "double":
        double_click_time = user32.GetDoubleClickTime() / 1000.0
        delay = double_click_time / 2 + random.uniform(0.01, 0.05)
        time.sleep(delay)
        _send_input(down)
        time.sleep(random.uniform(0.005, 0.03))
        _send_input(up)


def get_cursor_pos() -> tuple[int, int]:
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return (pt.x, pt.y)


def get_screen_size() -> tuple[int, int]:
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    return (w, h)