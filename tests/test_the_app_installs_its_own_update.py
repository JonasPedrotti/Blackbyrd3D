"""A found release is downloaded and installed from inside the app.

The installer had to be fetched in the browser and run by hand. Now the
Windows build runs it silently and is started again, and an AppImage swaps
itself. The release is not code-signed yet, so the SHA256 GitHub publishes
for each asset is what a download is checked against.
"""
import hashlib
import io
import os
import re
import time
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton

from blackbyrd3d import app as app_mod
from blackbyrd3d.app import MainWindow
from blackbyrd3d.utils import updates as u

ISS = (Path(__file__).resolve().parent.parent
       / "packaging" / "windows" / "installer.iss")

PAYLOAD = b"new build " * 5000
SHA = hashlib.sha256(PAYLOAD).hexdigest()


class _Resp(io.BytesIO):
    def __init__(self, data):
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data))}


def _opener(data=PAYLOAD):
    return lambda url: _Resp(data)


def test_a_release_brings_the_checksum_of_its_asset():
    rel = u.parse_release({"tag_name": "v9.0.0", "assets": [
        {"name": "Blackbyrd3D-Setup-x86_64.exe", "size": 12,
         "digest": "sha256:ABC123",
         "browser_download_url": "https://x/setup.exe"}]}, "Windows",
        "AMD64")
    assert rel["download"] == "https://x/setup.exe"
    assert rel["sha256"] == "abc123" and rel["size"] == 12


def test_a_release_without_a_checksum_is_not_installed():
    rel = {"download": "https://x/setup.exe", "sha256": None}
    assert u.can_install(rel, "windows") is False
    assert u.can_install({**rel, "sha256": SHA}, "windows") is True
    assert u.can_install({**rel, "sha256": SHA}, None) is False


def test_a_download_lands_only_when_its_checksum_matches(tmp_path):
    dest = str(tmp_path / "setup.exe")
    seen = []
    u.download("https://x", dest, SHA, opener=_opener(), chunk=4096,
               progress=lambda done, total: seen.append((done, total)))
    assert Path(dest).read_bytes() == PAYLOAD
    assert seen[-1] == (len(PAYLOAD), len(PAYLOAD))
    assert not Path(dest + ".part").exists()


def test_a_tampered_download_is_thrown_away(tmp_path):
    dest = str(tmp_path / "setup.exe")
    with pytest.raises(u.DownloadError):
        u.download("https://x", dest, SHA, opener=_opener(b"evil"))
    assert os.listdir(tmp_path) == []


def test_a_cancelled_download_leaves_nothing(tmp_path):
    dest = str(tmp_path / "setup.exe")
    with pytest.raises(u.DownloadCancelled):
        u.download("https://x", dest, SHA, opener=_opener(), chunk=4096,
                   cancelled=lambda: True)
    assert os.listdir(tmp_path) == []


def test_only_an_installed_build_installs_itself(tmp_path):
    image = tmp_path / "Blackbyrd3D.AppImage"
    image.write_bytes(b"old")
    assert u.install_kind("Windows", frozen=True, appimage=None) == "windows"
    assert u.install_kind("Windows", frozen=False, appimage=None) is None
    assert u.install_kind("Linux", frozen=True,
                          appimage=str(image)) == "appimage"
    assert u.install_kind("Linux", frozen=False, appimage=None) is None
    assert u.install_kind("Darwin", frozen=True, appimage=None) is None


def test_an_appimage_is_swapped_in_place(tmp_path):
    image = tmp_path / "Blackbyrd3D.AppImage"
    image.write_bytes(b"old")
    new = Path(u.appimage_download_path(str(image)))
    assert new.parent == tmp_path
    new.write_bytes(b"new")
    u.install_appimage(str(new), str(image))
    assert image.read_bytes() == b"new" and not new.exists()
    if os.name != "nt":
        assert os.access(image, os.X_OK)


def test_the_installer_runs_silently_as_an_update():
    cmd = u.windows_install_command("C:/t/setup.exe")
    assert cmd[0] == "C:/t/setup.exe"
    assert {"/SILENT", "/SUPPRESSMSGBOXES", "/UPDATE"} <= set(cmd)


def test_the_installer_waits_for_the_app_and_starts_it_again():
    iss = ISS.read_text()
    name = re.search(r'#define AppMutexName "([^"]+)"', iss).group(1)
    assert name == u.RUNNING_MUTEX
    assert "CheckForMutexes('{#AppMutexName}')" in iss
    run = re.search(r"\[Run\](.*?)\[Code\]", iss, re.S).group(1)
    assert "runasoriginaluser" in run and "Check: IsAppUpdate" in run


class _Main(QMainWindow):
    _on_update_available = MainWindow._on_update_available
    _download_update = MainWindow._download_update
    _open_update_page = MainWindow._open_update_page
    _install_update = MainWindow._install_update
    _update_failed = MainWindow._update_failed

    def __init__(self):
        super().__init__()
        self.dirty = False
        self.closed = False

    def close(self):
        self.closed = True
        return True


REL = {"version": "9.9.9", "url": "https://notes",
       "download": "https://setup", "sha256": SHA, "size": len(PAYLOAD)}


def _wait_for(cond, timeout=5.0):
    end = time.monotonic() + timeout
    while not cond() and time.monotonic() < end:
        QApplication.processEvents()
        time.sleep(0.01)
    assert cond()


def test_the_popup_offers_an_update_where_it_can_install(monkeypatch):
    monkeypatch.setattr(app_mod, "_can_install_update", lambda rel: True)
    win = _Main()
    win._on_update_available(REL)
    texts = {b.text() for b in win._update_box.findChildren(QPushButton)}
    assert "Update now" in texts
    assert "restarts" in win._update_box.body.text()


def test_an_appimage_updates_and_restarts_itself(monkeypatch, tmp_path):
    image = tmp_path / "Blackbyrd3D.AppImage"
    image.write_bytes(b"old")
    monkeypatch.setenv("APPIMAGE", str(image))
    monkeypatch.setattr(app_mod, "_update_install_kind", lambda: "appimage")
    monkeypatch.setattr(app_mod, "_can_install_update", lambda rel: True)
    monkeypatch.setattr(u, "_open", _opener())
    restarted = []
    monkeypatch.setattr(app_mod, "restart_app", restarted.append)
    win = _Main()
    win._pending_update = REL
    win._download_update()
    _wait_for(lambda: restarted)
    assert image.read_bytes() == PAYLOAD
    assert restarted == [win]


def test_windows_hands_over_to_the_installer_and_quits(monkeypatch,
                                                      tmp_path):
    monkeypatch.setattr(app_mod, "_update_install_kind", lambda: "windows")
    monkeypatch.setattr(app_mod, "_can_install_update", lambda rel: True)
    monkeypatch.setattr(u, "windows_download_path",
                        lambda: str(tmp_path / "setup.exe"))
    monkeypatch.setattr(u, "_open", _opener())
    started = []
    monkeypatch.setattr(u, "start_windows_installer", started.append)
    win = _Main()
    win._save_changes_first = lambda: True
    win._pending_update = REL
    win._download_update()
    _wait_for(lambda: win.closed)
    assert started == [str(tmp_path / "setup.exe")]
    assert win._restarting is True


def test_a_failed_update_falls_back_to_the_download_page(monkeypatch,
                                                        tmp_path):
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(app_mod, "_update_install_kind", lambda: "windows")
    monkeypatch.setattr(app_mod, "_can_install_update", lambda rel: True)
    monkeypatch.setattr(u, "windows_download_path",
                        lambda: str(tmp_path / "setup.exe"))
    monkeypatch.setattr(u, "_open", _opener(b"tampered"))
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: None))
    opened = []
    monkeypatch.setattr(QDesktopServices, "openUrl",
                        staticmethod(lambda url: opened.append(url.toString())))
    win = _Main()
    win._save_changes_first = lambda: True
    win._pending_update = REL
    win._download_update()
    _wait_for(lambda: opened)
    assert opened == ["https://setup"] and not win.closed


def _bgr(hex_rgb):
    r, g, b = hex_rgb[1:3], hex_rgb[3:5], hex_rgb[5:7]
    return f"$00{b}{g}{r}".upper()


def test_the_installer_draws_the_app_s_own_progress_bar():
    """The style's green bar looked like another program's."""
    from blackbyrd3d.ui import progress_card
    iss = ISS.read_text().upper()
    assert f"BARTRACKCOLOR = {_bgr(progress_card._TRACK.name())}" in iss
    assert f"BARFILLCOLOR = {_bgr(progress_card._FILL.name())}" in iss
    assert "PROGRESSGAUGE.VISIBLE := FALSE" in iss
    assert "PROCEDURE CURINSTALLPROGRESSCHANGED" in iss
