"""A first launch of Blackbyrd3D takes over Serpentine3D's settings and
plugins, and leaves Serpentine3D's own copy where it was."""

from __future__ import annotations

import json

from blackbyrd3d.utils import config


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    return tmp_path


def test_settings_and_plugins_are_copied_over(tmp_path, monkeypatch):
    home = _home(tmp_path, monkeypatch)
    (home / ".config" / "serpentine3d").mkdir(parents=True)
    (home / ".config" / "serpentine3d" / "settings.json").write_text("{}")
    (home / ".serpentine3d" / "plugins").mkdir(parents=True)
    (home / ".serpentine3d" / "plugins" / "greeble.py").write_text("")
    (home / ".serpentine3d" / "autosave").mkdir()

    config._adopt_serpentine_dirs()

    assert (home / ".config" / "blackbyrd3d" / "settings.json").exists()
    assert (home / ".blackbyrd3d" / "plugins" / "greeble.py").exists()
    assert not (home / ".blackbyrd3d" / "autosave").exists()
    assert (home / ".config" / "serpentine3d" / "settings.json").exists()


def test_settings_of_its_own_are_never_overwritten(tmp_path, monkeypatch):
    home = _home(tmp_path, monkeypatch)
    (home / ".config" / "serpentine3d").mkdir(parents=True)
    (home / ".config" / "serpentine3d" / "settings.json").write_text('{"a": 1}')
    (home / ".config" / "blackbyrd3d").mkdir(parents=True)
    (home / ".config" / "blackbyrd3d" / "settings.json").write_text('{"a": 2}')

    config._adopt_serpentine_dirs()

    stored = (home / ".config" / "blackbyrd3d" / "settings.json").read_text()
    assert json.loads(stored) == {"a": 2}

