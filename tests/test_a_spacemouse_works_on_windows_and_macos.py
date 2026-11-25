"""A SpaceMouse drives the view on Windows and macOS too (#178).

Linux reads it through spacenavd or evdev. Windows now reads the device's
HID reports through Raw Input, and macOS the 3Dconnexion driver's device
states through its framework. Neither has been tried on real hardware, so
what is tested here is that both turn the same deflection into the same
motion evdev does, which was calibrated in the hand, and that buttons
press and release once each.
"""

from __future__ import annotations

import ctypes
import struct

import pytest

from blackbyrd3d.ui import spacemouse as sm
from blackbyrd3d.ui import spacemouse_mac as mac
from blackbyrd3d.ui import spacemouse_win as win


def _evdev_motion(values):
    """What the evdev reader made of six raw axes before it shared
    hid_motion: the calibrated reference."""
    order = (0, 2, 1, 3, 5, 4)
    sign = (1, -1, -1, 1, -1, -1)
    motion = [0.0] * 6
    for code, value in enumerate(values):
        motion[order[code]] += value * sign[code] * (sm._FULL / 500.0)
    return motion


AXES = (120, -40, 300, -7, 55, -350)


# -- the HID reports Windows hands over ---------------------------------------

def test_a_six_axis_report_moves_as_evdev_does():
    motion, buttons = sm.HidReports().read(
        struct.pack("<B6h", 1, *AXES))
    assert motion == pytest.approx(_evdev_motion(AXES))
    assert buttons == []


def test_older_devices_send_translation_and_rotation_apart():
    reports = sm.HidReports()
    moved, _ = reports.read(struct.pack("<B3h", 1, *AXES[:3]))
    turned, _ = reports.read(struct.pack("<B3h", 2, *AXES[3:]))
    together = [a + b for a, b in zip(moved, turned)]
    assert together == pytest.approx(_evdev_motion(AXES))


def test_a_button_presses_and_releases_once():
    reports = sm.HidReports()
    assert reports.read(bytes([3, 0b10, 0])) == (None, [(1, True)])
    assert reports.read(bytes([3, 0b10, 0])) == (None, [])
    assert reports.read(bytes([3, 0b01, 0])) == (None, [(0, True),
                                                        (1, False)])


def test_an_unknown_report_is_ignored():
    assert sm.HidReports().read(bytes([7, 1, 2, 3])) == (None, [])
    assert sm.HidReports().read(b"") == (None, [])


def test_a_raw_input_buffer_holds_its_reports_in_turn():
    header = 24
    first = struct.pack("<B6h", 1, *AXES)
    second = struct.pack("<B6h", 1, *(-v for v in AXES))
    buf = (struct.pack("<II", win.RIM_TYPEHID, 0) + bytes(header - 8)
           + struct.pack("<II", len(first), 2) + first + second)
    assert win.hid_reports_in(buf, header) == [first, second]


def test_a_raw_input_buffer_that_is_not_a_hid_device_holds_nothing():
    buf = struct.pack("<II", 0, 0) + bytes(16) + struct.pack("<II", 13, 1)
    assert win.hid_reports_in(buf + bytes(13), 24) == []
    assert win.hid_reports_in(b"\x02", 24) == []


class _Navigator:
    def __init__(self):
        self._hid = sm.HidReports()
        self.applied = []

    def _apply(self, motion, buttons):
        self.applied.append((motion, buttons))

    hid_report = sm.SpaceMouseNavigator.hid_report


def test_wm_input_reaches_the_navigator(monkeypatch):
    report = struct.pack("<B6h", 1, *AXES)
    buf = (struct.pack("<II", win.RIM_TYPEHID, 0)
           + bytes(win.HEADER_SIZE - 8)
           + struct.pack("<II", len(report), 1) + report)
    monkeypatch.setattr(win, "_read_rawinput", lambda handle: buf)
    nav = _Navigator()
    filt = win._RawInputFilter()
    filt.listeners.add(nav)
    msg = win.MSG(None, win.WM_INPUT, 0, 1234)
    result = filt.nativeEventFilter(b"windows_generic_MSG",
                                    ctypes.addressof(msg))
    assert result == (False, 0), "WM_INPUT must still reach Windows"
    assert len(nav.applied) == 1
    assert nav.applied[0][0] == pytest.approx(_evdev_motion(AXES))


def test_other_messages_are_left_alone(monkeypatch):
    monkeypatch.setattr(win, "_read_rawinput",
                        lambda handle: pytest.fail("read a non-input msg"))
    nav = _Navigator()
    filt = win._RawInputFilter()
    filt.listeners.add(nav)
    msg = win.MSG(None, 0x0200, 0, 0)               # WM_MOUSEMOVE
    filt.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(msg))
    assert nav.applied == []


# -- the device states the Mac driver hands over -------------------------------

def test_the_device_state_is_laid_out_as_the_driver_writes_it():
    s = mac.ConnexionDeviceState
    assert ctypes.sizeof(s) == 48
    assert s.axis.offset == 30
    assert s.buttons.offset == 44


def _state(client=7, command=mac.CMD_HANDLE_AXIS, axes=AXES, buttons=0):
    state = mac.ConnexionDeviceState()
    state.client, state.command, state.buttons = client, command, buttons
    state.axis[:] = axes
    return state


def test_a_mac_axis_state_moves_as_evdev_does():
    motion, buttons = mac.ConnexionStates(7).read(_state())
    assert motion == pytest.approx(_evdev_motion(AXES))
    assert buttons == []


def test_a_state_for_another_client_is_ignored():
    assert mac.ConnexionStates(7).read(_state(client=8)) == (None, [])


def test_mac_buttons_press_and_release_once():
    states = mac.ConnexionStates(7)
    press = _state(command=mac.CMD_HANDLE_BUTTONS, buttons=0b100)
    release = _state(command=mac.CMD_HANDLE_BUTTONS, buttons=0)
    assert states.read(press) == (None, [(2, True)])
    assert states.read(release) == (None, [(2, False)])


def test_the_driver_s_message_reaches_the_navigator():
    client = mac._Client(lib=None)
    client.states = mac.ConnexionStates(7)
    nav = _Navigator()
    client.listeners.add(nav)
    state = _state()
    client._message(0, mac.MSG_DEVICE_STATE, ctypes.addressof(state))
    client._message(0, 0x12345678, ctypes.addressof(state))
    assert len(nav.applied) == 1
    assert nav.applied[0][0] == pytest.approx(_evdev_motion(AXES))


def test_the_process_name_is_a_pascal_string():
    assert mac.pascal_name("python3") == b"\x07python3"
