import pytest

from blackbyrd3d import launcher


@pytest.fixture
def linux(monkeypatch):
    monkeypatch.setattr(launcher.sys, "platform", "linux")
    for name in ("WAYLAND_DISPLAY", "QT_QPA_PLATFORM", "BYRD3D_WAYLAND"):
        # set first, so the original value is put back after the test
        monkeypatch.setenv(name, "")
        monkeypatch.delenv(name)
    return monkeypatch


def test_a_wayland_desktop_asks_for_xwayland_first(linux):
    linux.setenv("WAYLAND_DISPLAY", "wayland-0")
    launcher._prefer_xwayland()
    assert launcher.os.environ["QT_QPA_PLATFORM"] == "xcb;wayland"


def test_a_platform_asked_for_is_kept(linux):
    linux.setenv("WAYLAND_DISPLAY", "wayland-0")
    linux.setenv("QT_QPA_PLATFORM", "wayland")
    launcher._prefer_xwayland()
    assert launcher.os.environ["QT_QPA_PLATFORM"] == "wayland"


def test_native_wayland_can_be_asked_for(linux):
    linux.setenv("WAYLAND_DISPLAY", "wayland-0")
    linux.setenv("BYRD3D_WAYLAND", "1")
    launcher._prefer_xwayland()
    assert "QT_QPA_PLATFORM" not in launcher.os.environ


def test_x11_and_other_systems_are_left_alone(linux):
    launcher._prefer_xwayland()
    assert "QT_QPA_PLATFORM" not in launcher.os.environ
    linux.setenv("WAYLAND_DISPLAY", "wayland-0")
    linux.setattr(launcher.sys, "platform", "win32")
    launcher._prefer_xwayland()
    assert "QT_QPA_PLATFORM" not in launcher.os.environ
