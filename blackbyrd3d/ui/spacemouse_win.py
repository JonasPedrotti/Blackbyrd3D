"""SpaceMouse on Windows: the device's HID reports through Raw Input.

The program asks Windows for the input of every multi-axis controller,
which is what a 3Dconnexion device says it is, and reads the reports out
of WM_INPUT as they reach whichever of its windows has the focus. This
works with or without the 3Dconnexion driver installed; with it, the
driver may also turn the puck into scrolling for programs it does not
know, which its settings can switch off for Blackbyrd3D.

Untested on real hardware so far.
"""

from __future__ import annotations

import ctypes
import struct
import weakref

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication

WM_INPUT = 0x00FF
RID_INPUT = 0x10000003
RIM_TYPEHID = 2
USAGE_PAGE_GENERIC = 0x01
USAGE_MULTI_AXIS = 0x08


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [("usUsagePage", ctypes.c_ushort),
                ("usUsage", ctypes.c_ushort),
                ("dwFlags", ctypes.c_uint32),
                ("hwndTarget", ctypes.c_void_p)]


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [("dwType", ctypes.c_uint32),
                ("dwSize", ctypes.c_uint32),
                ("hDevice", ctypes.c_void_p),
                ("wParam", ctypes.c_size_t)]


class MSG(ctypes.Structure):
    _fields_ = [("hwnd", ctypes.c_void_p),
                ("message", ctypes.c_uint),
                ("wParam", ctypes.c_size_t),
                ("lParam", ctypes.c_ssize_t)]


HEADER_SIZE = ctypes.sizeof(RAWINPUTHEADER)


def hid_reports_in(buf: bytes, header_size: int = HEADER_SIZE) -> list[bytes]:
    """The HID reports one RAWINPUT holds: a header, then the size of each
    report and their count, then the reports one after another."""
    if len(buf) < header_size + 8:
        return []
    if struct.unpack_from("<I", buf, 0)[0] != RIM_TYPEHID:
        return []
    size, count = struct.unpack_from("<II", buf, header_size)
    start = header_size + 8
    if size == 0 or start + size * count > len(buf):
        return []
    return [buf[start + i * size:start + (i + 1) * size]
            for i in range(count)]


def _read_rawinput(handle) -> bytes:
    user32 = ctypes.windll.user32
    size = ctypes.c_uint(0)
    user32.GetRawInputData(ctypes.c_void_p(handle), RID_INPUT, None,
                           ctypes.byref(size), HEADER_SIZE)
    if not size.value:
        return b""
    buf = ctypes.create_string_buffer(size.value)
    got = user32.GetRawInputData(ctypes.c_void_p(handle), RID_INPUT, buf,
                                 ctypes.byref(size), HEADER_SIZE)
    if got in (0, 0xFFFFFFFF):
        return b""
    return buf.raw[:got]


class _RawInputFilter(QAbstractNativeEventFilter):
    """Hands each multi-axis HID report to every listening navigator."""

    def __init__(self):
        super().__init__()
        self.listeners = weakref.WeakSet()

    def nativeEventFilter(self, event_type, message):
        if bytes(event_type) == b"windows_generic_MSG":
            try:
                msg = MSG.from_address(int(message))
                if msg.message == WM_INPUT:
                    for report in hid_reports_in(_read_rawinput(msg.lParam)):
                        for navigator in list(self.listeners):
                            navigator.hid_report(report)
            except Exception:                              # noqa: BLE001
                pass            # a bad report must not break the event loop
        return False, 0


_filter = None


def listen(navigator) -> bool:
    """Send this navigator the SpaceMouse's reports. False if Windows
    would not register for them."""
    global _filter
    if _filter is None:
        device = RAWINPUTDEVICE(USAGE_PAGE_GENERIC, USAGE_MULTI_AXIS, 0, None)
        try:
            ok = ctypes.windll.user32.RegisterRawInputDevices(
                ctypes.byref(device), 1, ctypes.sizeof(device))
        except (AttributeError, OSError):
            return False
        if not ok:
            return False
        _filter = _RawInputFilter()
        QCoreApplication.instance().installNativeEventFilter(_filter)
    _filter.listeners.add(navigator)
    return True
