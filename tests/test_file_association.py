"""Offering to be the default application for .byrd files.

Beta feedback: nothing ever asks. The offer is one dialog on launch
(app.py wires it); everything decidable without a screen lives in
utils/file_assoc.py and is what these tests pin down.
"""

import ntpath
import posixpath
import subprocess

import pytest

import blackbyrd3d.commands  # registers all commands  # noqa: F401
from blackbyrd3d.utils import file_assoc
from blackbyrd3d.utils.config import Config


@pytest.fixture
def config(tmp_path):
    return Config(path=str(tmp_path / "settings.json"))


def _own_home(monkeypatch, tmp_path):
    """Give the test a home directory of its own, on any platform.

    HOME alone is a posix answer: expanduser("~") is ntpath's on Windows,
    and that reads USERPROFILE. Both, plus no XDG_DATA_HOME, is what puts
    the whole of _data_home() inside tmp_path wherever this runs.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)


@pytest.mark.parametrize("flavour", [posixpath, ntpath],
                         ids=["posix", "windows"])
def test_the_home_a_test_sets_is_the_home_that_gets_used(
        monkeypatch, tmp_path, flavour):
    """Pointing HOME at a tmp_path only isolates the run on posix.

    expanduser("~") is ntpath's on Windows, and that one reads USERPROFILE
    and never looks at HOME. So make_default went on writing into the real
    user profile while the assertions below looked at an empty tmp_path,
    and the only reason it showed up as a failure rather than as a mess is
    that the .desktop file was not where the test expected it.
    """
    _own_home(monkeypatch, tmp_path)
    monkeypatch.setattr(file_assoc.os.path, "expanduser", flavour.expanduser)
    assert file_assoc._data_home().startswith(str(tmp_path))


# ------------------------------------------------- what gets registered

def test_desktop_entry_names_the_app_and_its_mime_type():
    text = file_assoc.desktop_entry("/opt/Blackbyrd3D.AppImage %F")
    assert "[Desktop Entry]" in text
    assert "Exec=/opt/Blackbyrd3D.AppImage %F" in text
    assert f"MimeType={file_assoc.MIME};" in text
    assert "Name=Blackbyrd3D" in text


def test_mime_xml_claims_the_serp_glob():
    xml = file_assoc.mime_xml()
    assert file_assoc.MIME in xml
    assert '*.byrd' in xml


def test_exec_line_prefers_the_appimage_it_runs_from(monkeypatch):
    monkeypatch.setenv("APPIMAGE", "/home/u/Applications/S.AppImage")
    assert file_assoc.exec_line() == "/home/u/Applications/S.AppImage %F"
    monkeypatch.delenv("APPIMAGE")
    line = file_assoc.exec_line()
    assert "-m blackbyrd3d" in line and "%F" in line


# ------------------------------------------------------- status probing

def test_status_reads_xdg_mime_answer(monkeypatch):
    monkeypatch.setattr(file_assoc.sys, "platform", "linux")

    def fake_run(cmd, **kw):
        assert cmd[:3] == ["xdg-mime", "query", "default"]
        return subprocess.CompletedProcess(cmd, 0,
                                           stdout="blackbyrd3d.desktop\n")
    monkeypatch.setattr(file_assoc.subprocess, "run", fake_run)
    assert file_assoc.status() == "default"

    def other(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, stdout="org.gnome.x\n")
    monkeypatch.setattr(file_assoc.subprocess, "run", other)
    assert file_assoc.status() == "not_default"

    def boom(cmd, **kw):
        raise FileNotFoundError("no xdg-mime")
    monkeypatch.setattr(file_assoc.subprocess, "run", boom)
    assert file_assoc.status() == "unknown"


# ------------------------------------------------------- the offer rule

def test_offers_once_until_answered(monkeypatch, config):
    monkeypatch.setattr(file_assoc, "status", lambda: "not_default")
    assert file_assoc.should_offer(config)
    config.set("file_assoc", "asked", True)
    assert not file_assoc.should_offer(config)


def test_never_offers_when_already_default(monkeypatch, config):
    monkeypatch.setattr(file_assoc, "status", lambda: "default")
    assert not file_assoc.should_offer(config)


# --------------------------------------------- making it stick on linux

def test_make_default_registers_and_sets_the_handler(monkeypatch, tmp_path):
    monkeypatch.setattr(file_assoc.sys, "platform", "linux")
    _own_home(monkeypatch, tmp_path)
    monkeypatch.setenv("APPIMAGE", "/apps/S.AppImage")
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="")
    monkeypatch.setattr(file_assoc.subprocess, "run", fake_run)

    ok, msg = file_assoc.make_default()
    assert ok, msg
    share = tmp_path / ".local" / "share"
    desktop = share / "applications" / "blackbyrd3d.desktop"
    assert desktop.exists()
    assert "Exec=/apps/S.AppImage %F" in desktop.read_text()
    assert (share / "mime" / "packages" / "blackbyrd3d.xml").exists()
    assert ["xdg-mime", "default", "blackbyrd3d.desktop",
            file_assoc.MIME] in calls
    assert ".byrd" in msg


def test_make_default_keeps_an_existing_desktop_entry(monkeypatch, tmp_path):
    """install-desktop.sh writes a richer entry; ours must not clobber it."""
    monkeypatch.setattr(file_assoc.sys, "platform", "linux")
    _own_home(monkeypatch, tmp_path)
    apps = tmp_path / ".local" / "share" / "applications"
    apps.mkdir(parents=True)
    (apps / "blackbyrd3d.desktop").write_text("[Desktop Entry]\nName=Rich\n")
    monkeypatch.setattr(
        file_assoc.subprocess, "run",
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout=""))
    ok, _ = file_assoc.make_default()
    assert ok
    assert "Name=Rich" in (apps / "blackbyrd3d.desktop").read_text()


# ----------------------------------------------------- the command form

def test_setdefaultapp_command_reports_what_happened(monkeypatch):
    from blackbyrd3d.commands.base import (
        CommandContext,
        CommandProcessor,
    )
    from blackbyrd3d.core.history import History
    from blackbyrd3d.core.scene import Scene
    from blackbyrd3d.core.selection import SelectionManager

    scene = Scene()
    ctx = CommandContext(scene, SelectionManager(scene), History(scene))
    proc = CommandProcessor(ctx)
    echoes = []
    ctx.add_echo_listener(echoes.append)
    monkeypatch.setattr(file_assoc, "make_default",
                        lambda: (True, "Blackbyrd3D now opens .byrd files."))
    proc.run("setdefaultapp")
    assert not proc.busy
    assert any(".byrd" in e for e in echoes)


# --------------------------------------- macOS FileOpen events reach us

class _FakeFileOpen:
    def __init__(self, path):
        self._path = path

    def type(self):
        from PySide6.QtCore import QEvent
        return QEvent.Type.FileOpen

    def file(self):
        return self._path


def test_file_open_events_open_the_document(monkeypatch, tmp_path):
    monkeypatch.setenv("BYRD3D_CONFIG", str(tmp_path / "s.json"))
    monkeypatch.setenv("BYRD3D_NO_RECOVER", "1")
    from blackbyrd3d.app import FileOpenRelay

    opened = []

    class _Window:
        def _open_path(self, path):
            opened.append(path)

    relay = FileOpenRelay.__new__(FileOpenRelay)   # no QObject parent needed
    relay._window = _Window()
    handled = FileOpenRelay.eventFilter(relay, None,
                                        _FakeFileOpen("/tmp/a.byrd"))
    assert handled and opened == ["/tmp/a.byrd"]


# ------------------------------------------- .wyrm, icons, moves, removal

def _linux_home(monkeypatch, tmp_path, appimage="/apps/S.AppImage"):
    monkeypatch.setattr(file_assoc.sys, "platform", "linux")
    _own_home(monkeypatch, tmp_path)
    monkeypatch.setenv("APPIMAGE", appimage)
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="")
    monkeypatch.setattr(file_assoc.subprocess, "run", fake_run)
    return tmp_path / ".local" / "share", calls


def test_wyrm_graphs_are_claimed_beside_models(monkeypatch, tmp_path):
    share, calls = _linux_home(monkeypatch, tmp_path)
    ok, msg = file_assoc.make_default()
    assert ok and ".wyrm" in msg
    xml = (share / "mime" / "packages" / "blackbyrd3d.xml").read_text()
    assert '*.wyrm' in xml and file_assoc.WYRM_MIME in xml
    desktop = (share / "applications" / "blackbyrd3d.desktop").read_text()
    assert file_assoc.WYRM_MIME in desktop
    assert ["xdg-mime", "default", "blackbyrd3d.desktop",
            file_assoc.WYRM_MIME] in calls


def test_the_app_and_its_files_get_their_icons(monkeypatch, tmp_path):
    share, _ = _linux_home(monkeypatch, tmp_path)
    file_assoc.make_default()
    icons = share / "icons" / "hicolor" / "256x256"
    for path in (icons / "apps" / "blackbyrd3d.png",
                 icons / "mimetypes" / "application-x-blackbyrd3d.png",
                 icons / "mimetypes" / "application-x-blackbyrd3d-wyrm.png"):
        assert path.stat().st_size > 0, path
    xml = (share / "mime" / "packages" / "blackbyrd3d.xml").read_text()
    assert '<icon name="application-x-blackbyrd3d-wyrm"/>' in xml


def test_a_moved_appimage_is_followed(monkeypatch, tmp_path):
    share, _ = _linux_home(monkeypatch, tmp_path, "/old/S.AppImage")
    file_assoc.make_default()
    monkeypatch.setenv("APPIMAGE", "/new/Blackbyrd3D-0.2.AppImage")
    assert file_assoc.follow_the_appimage()
    desktop = (share / "applications" / "blackbyrd3d.desktop").read_text()
    assert "Exec=/new/Blackbyrd3D-0.2.AppImage %F" in desktop
    assert not file_assoc.follow_the_appimage(), "nothing left to follow"


def test_a_checkout_s_entry_is_not_taken_over(monkeypatch, tmp_path):
    """install-desktop.sh --venv starts the working copy; an AppImage run
    now and then must not point the menu away from it."""
    share, _ = _linux_home(monkeypatch, tmp_path)
    apps = share / "applications"
    apps.mkdir(parents=True)
    entry = "[Desktop Entry]\nExec=/src/.venv/bin/python -m blackbyrd3d.app %F\n"
    (apps / "blackbyrd3d.desktop").write_text(entry)
    assert not file_assoc.follow_the_appimage()
    assert (apps / "blackbyrd3d.desktop").read_text() == entry


def test_nothing_is_written_when_nothing_was_set_up(monkeypatch, tmp_path):
    share, _ = _linux_home(monkeypatch, tmp_path)
    assert not file_assoc.follow_the_appimage()
    assert not (share / "applications").exists()


def test_the_registration_can_be_taken_back(monkeypatch, tmp_path):
    share, _ = _linux_home(monkeypatch, tmp_path)
    file_assoc.make_default()
    ok, msg = file_assoc.remove_from_desktop()
    assert ok, msg
    assert not (share / "applications" / "blackbyrd3d.desktop").exists()
    assert not (share / "mime" / "packages" / "blackbyrd3d.xml").exists()
    assert not list((share / "icons").rglob("*.png"))
