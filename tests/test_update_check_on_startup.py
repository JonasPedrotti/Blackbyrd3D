"""Check for updates on startup works on Windows once it is ticked.

Ticking the installer's task did nothing when an earlier install had cleared
it, the app had no switch of its own to turn it back on, and a release found
on launch was announced in a timed status message that the next status
refresh wiped before anyone read it.
"""
from pathlib import Path

import pytest
from PySide6.QtWidgets import QMainWindow, QPushButton, QWidget

from blackbyrd3d.app import MainWindow
from blackbyrd3d.core.scene import Scene
from blackbyrd3d.core.selection import SelectionManager
from blackbyrd3d.ui import viewport as vp_mod
from blackbyrd3d.ui.settings_dialog import SettingsDialog
from blackbyrd3d.utils.config import Config

ISS = (Path(__file__).resolve().parent.parent
       / "packaging" / "windows" / "installer.iss")


class _Window(QWidget):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        scene = Scene()
        self.viewport = vp_mod.Viewport(scene, SelectionManager(scene),
                                        config=cfg)
        self.osnap_bar = type("_Bar", (), {"refresh": lambda self: None})()
        self.manual_checks = 0

    def apply_user_shortcuts(self):
        pass

    def apply_user_aliases(self):
        pass

    def _check_updates_manual(self):
        self.manual_checks += 1


@pytest.fixture
def dlg(tmp_path):
    cfg = Config(path=str(tmp_path / "settings.json"))
    win = _Window(cfg)
    return SettingsDialog(win), cfg, win


def test_settings_show_the_switch_as_stored(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"check_updates": false}')
    cfg = Config(path=str(path))
    d = SettingsDialog(_Window(cfg))
    assert d.cb_check_updates.isChecked() is False


def test_ticking_the_switch_turns_the_check_back_on(dlg, tmp_path):
    d, cfg, _ = dlg
    d.cb_check_updates.setChecked(False)
    assert Config(path=cfg.path).get("check_updates") is False
    d.cb_check_updates.setChecked(True)
    assert Config(path=cfg.path).get("check_updates") is True


def test_check_now_runs_the_manual_check(dlg):
    d, _, win = dlg
    btn = next(b for b in d.findChildren(QPushButton)
               if b.text() == "Check Now")
    btn.click()
    assert win.manual_checks == 1


class _Main(QMainWindow):
    _on_update_available = MainWindow._on_update_available
    _open_update_notice = MainWindow._open_update_notice
    _on_update_none = MainWindow._on_update_none
    UPDATE_NOTE_MS = MainWindow.UPDATE_NOTE_MS

    def __init__(self):
        super().__init__()
        self.manual_checks = 0

    def _check_updates_manual(self):
        self.manual_checks += 1


def test_a_found_release_stays_in_the_status_bar():
    win = _Main()
    win._on_update_available({"version": "9.9.9", "url": "", "download": ""})
    win.statusBar().showMessage("3 object(s)  ·  0 selected")
    btn = win._update_button
    assert "9.9.9" in btn.text()
    assert not btn.isHidden()
    btn.click()
    assert win.manual_checks == 1
    win._on_update_available({"version": "9.9.10", "url": "", "download": ""})
    assert len(win.statusBar().findChildren(QPushButton)) == 1
    assert "9.9.10" in win._update_button.text()


def test_the_notice_goes_once_it_has_been_clicked():
    """Clicked, it has done its job: the download dialog says the rest,
    and a notice that stays would be one more thing in the window."""
    win = _Main()
    win._on_update_available({"version": "9.9.9", "url": "", "download": ""})
    win._update_button.click()
    assert win.manual_checks == 1
    assert win._update_button.isHidden()
    # a newer one found later is announced again
    win._on_update_available({"version": "9.9.10", "url": "", "download": ""})
    assert not win._update_button.isHidden()


def test_installer_applies_a_ticked_task_to_an_existing_file():
    iss = ISS.read_text()
    assert "'\"check_updates\": true'" in iss
    assert "'\"check_updates\": false'" in iss
    assert "SaveStringToFile(CfgPath, Json" in iss


def test_a_check_that_finds_nothing_says_so():
    """A ticked check that found nothing newer looked exactly like one that
    never ran, so it read as the installer's choice being ignored."""
    from blackbyrd3d import __version__
    win = _Main()
    win._on_update_none(True)
    assert win._update_note.text() == f"Blackbyrd3D {__version__} is up to date"
    assert not win._update_note.isHidden()
    win._on_update_none(False)
    assert "Could not reach GitHub" in win._update_note.text()


def test_the_launch_check_reports_back_either_way(monkeypatch):
    """start_update_check emits one of its two signals, never neither."""
    import threading

    from blackbyrd3d.utils import updates
    got = []

    class _Fake:
        cfg = Config(path="nonexistent-settings.json")
        updateAvailable = type("S", (), {"emit": lambda self, r: got.append(("new", r))})()
        updateUpToDate = type("S", (), {"emit": lambda self, ok: got.append(("none", ok))})()

    class _Now(threading.Thread):
        def start(self):
            self.run()
    monkeypatch.setattr(threading, "Thread", _Now)
    monkeypatch.delenv("BYRD3D_NO_UPDATE_CHECK", raising=False)
    from PySide6.QtWidgets import QApplication
    monkeypatch.setattr(QApplication, "platformName", staticmethod(lambda: "windows"))

    monkeypatch.setattr(updates, "_fetch", lambda: '{"tag_name": "v0.0.1"}')
    MainWindow.start_update_check(_Fake())
    assert got == [("none", True)]

    got.clear()

    def offline():
        raise OSError("offline")
    monkeypatch.setattr(updates, "_fetch", offline)
    MainWindow.start_update_check(_Fake())
    assert got == [("none", False)]
