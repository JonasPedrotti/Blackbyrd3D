"""SpaceMouse on macOS: the 3Dconnexion driver's own framework.

On a Mac the driver (3DxWare) holds the device, so its state is read
through 3DconnexionClient.framework, which it installs. Its callbacks
arrive on the main run loop, which Qt runs, so they land on the GUI
thread like any other event. Without the driver there is no source.

Untested on real hardware so far.
"""

from __future__ import annotations

import ctypes
import os
import sys
import weakref

from .spacemouse import button_changes, hid_motion

FRAMEWORK = ("/Library/Frameworks/3DconnexionClient.framework/"
             "3DconnexionClient")

CLIENT_WILDCARD = 0x2A2A2A2A            # '****': match by process name
MODE_TAKE_OVER = 1
MASK_ALL = 0x3FFF
ALL_BUTTONS = 0xFFFFFFFF
MSG_DEVICE_STATE = 0x33645352           # '3dSR'
CMD_HANDLE_BUTTONS = 2
CMD_HANDLE_AXIS = 3


class ConnexionDeviceState(ctypes.Structure):
    _pack_ = 2
    _fields_ = [("version", ctypes.c_uint16),
                ("client", ctypes.c_uint16),
                ("command", ctypes.c_uint16),
                ("param", ctypes.c_int16),
                ("value", ctypes.c_int32),
                ("time", ctypes.c_uint64),
                ("report", ctypes.c_uint8 * 8),
                ("buttons8", ctypes.c_uint16),
                ("axis", ctypes.c_int16 * 6),
                ("address", ctypes.c_uint16),
                ("buttons", ctypes.c_uint32)]


MessageHandler = ctypes.CFUNCTYPE(None, ctypes.c_uint32, ctypes.c_uint32,
                                  ctypes.c_void_p)
DeviceHandler = ctypes.CFUNCTYPE(None, ctypes.c_uint32)


class ConnexionStates:
    """The driver's device states, as navigator input."""

    def __init__(self, client: int):
        self.client = client
        self.buttons = 0

    def read(self, state: ConnexionDeviceState):
        """(motion, buttons) for one state; motion None if it moved
        nothing."""
        if state.client != self.client:
            return None, []
        if state.command == CMD_HANDLE_AXIS:
            return hid_motion(enumerate(state.axis)), []
        if state.command == CMD_HANDLE_BUTTONS:
            changes = button_changes(self.buttons, state.buttons)
            self.buttons = state.buttons
            return None, changes
        return None, []


def pascal_name(name: str) -> bytes:
    """The process name as the driver matches it: a Pascal string."""
    raw = name.encode("utf-8")[:255]
    return bytes([len(raw)]) + raw


class _Client:
    """The one registration with the driver, shared by every navigator."""

    def __init__(self, lib):
        self.lib = lib
        self.listeners = weakref.WeakSet()
        self.states = None
        # held for as long as the driver may call them
        self._on_message = MessageHandler(self._message)
        self._on_device = DeviceHandler(lambda _product: None)

    def register(self) -> bool:
        lib = self.lib
        setter = getattr(lib, "SetConnexionHandlers", None)
        if setter is not None:
            setter.argtypes = [MessageHandler, DeviceHandler, DeviceHandler,
                               ctypes.c_bool]
            setter.restype = ctypes.c_int16
            err = setter(self._on_message, self._on_device, self._on_device,
                         False)
        else:
            installer = lib.InstallConnexionHandlers
            installer.argtypes = [MessageHandler, DeviceHandler,
                                  DeviceHandler]
            installer.restype = ctypes.c_int16
            err = installer(self._on_message, self._on_device,
                            self._on_device)
        if err:
            return False
        lib.RegisterConnexionClient.argtypes = [
            ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint16,
            ctypes.c_uint32]
        lib.RegisterConnexionClient.restype = ctypes.c_uint16
        name = pascal_name(os.path.basename(sys.executable))
        client = lib.RegisterConnexionClient(CLIENT_WILDCARD, name,
                                             MODE_TAKE_OVER, MASK_ALL)
        if not client:
            return False
        mask = getattr(lib, "SetConnexionClientButtonMask", None)
        if mask is not None:
            mask.argtypes = [ctypes.c_uint16, ctypes.c_uint32]
            mask(client, ALL_BUTTONS)
        self.states = ConnexionStates(client)
        return True

    def _message(self, _product, kind, argument):
        try:
            if kind != MSG_DEVICE_STATE or not argument or self.states is None:
                return
            state = ConnexionDeviceState.from_address(argument)
            motion, buttons = self.states.read(state)
            if motion is None and not buttons:
                return
            for navigator in list(self.listeners):
                navigator._apply(motion or [0.0] * 6, buttons)
        except Exception:                                  # noqa: BLE001
            pass                # never raise back into the driver


_client = None


def listen(navigator) -> bool:
    """Send this navigator the SpaceMouse's motion. False without the
    3Dconnexion driver."""
    global _client
    if _client is None:
        try:
            lib = ctypes.CDLL(FRAMEWORK)
        except OSError:
            return False
        client = _Client(lib)
        try:
            if not client.register():
                return False
        except (AttributeError, OSError):
            return False
        _client = client
    _client.listeners.add(navigator)
    return True
