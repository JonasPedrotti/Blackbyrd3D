"""The Windows installer offers, ticked, to make Blackbyrd3D the default app
for .byrd and .wyrm, and is dressed in the app's own colours and marks."""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIN = ROOT / "packaging" / "windows"
ISS = (WIN / "installer.iss").read_text()


def _entry(subkey: str) -> str:
    """The [Registry] line that sets the default value of `subkey`."""
    for line in re.split(r"(?m)^(?=Root:)", ISS):
        if f'Subkey: "{subkey}";' in line and 'ValueName: "";' in line:
            return line
    raise AssertionError(f"no entry for {subkey}")


def test_the_default_app_task_is_there_and_ticked():
    task = re.search(r'(?ms)^Name: "fileassoc";.*?(?=^Name:|^\[)', ISS)
    assert task, "installer.iss has no fileassoc task"
    assert "unchecked" not in task.group(0)


def test_only_the_ticked_task_makes_us_the_default():
    assert "Tasks: fileassoc" in _entry(r"Software\Classes\.byrd")
    assert "Tasks: fileassoc" in _entry(r"Software\Classes\.wyrm")


def test_a_choice_made_in_settings_does_not_win_over_the_ticked_task():
    assert r"\UserChoice'" in ISS
    assert "ApplyFileAssoc('.byrd', 'Blackbyrd3D.Document')" in ISS
    assert "ApplyFileAssoc('.wyrm', 'Blackbyrd3D.Wyrm')" in ISS


def test_the_app_learns_the_installer_already_asked():
    assert 'ValueName: "AssociateFiles"' in ISS


def test_the_wizard_is_dark_like_the_app():
    assert re.search(r"(?m)^WizardStyle=.*\bdark\b", ISS)
    assert "WizardBackColor=#2b2b2b" in ISS
    assert "WizardImageFile=wizard\\" in ISS
    assert "WizardSmallImageFile=wizard\\" in ISS


def test_the_options_page_goes_without_the_corner_mark():
    assert ("WizardSmallBitmapImage.Visible := CurPageID <> wpSelectTasks"
            in ISS)


def test_the_text_sits_in_the_middle_of_its_page():
    for page in ("WelcomePage", "SelectTasksPage", "FinishedPage"):
        assert f"F.{page}.ClientHeight" in ISS


def test_the_build_draws_the_wizard_images_before_compiling():
    ps1 = (WIN / "build-installer.ps1").read_text()
    draw = ps1.find("make_wizard_images.py")
    iscc = ps1.find("& $iscc installer.iss")
    assert draw != -1 and iscc != -1 and draw < iscc


def test_the_wizard_images_come_out_in_every_size(tmp_path):
    out = subprocess.run(
        [sys.executable, str(WIN / "make_wizard_images.py"), str(tmp_path)],
        capture_output=True, text=True, timeout=120, check=True)
    names = set(out.stdout.split())
    assert "wizard-202x386.png" in names and "wizard-534x1022.png" in names
    assert "wizard-small-58.png" in names and "wizard-small-159.png" in names
    assert all((tmp_path / n).stat().st_size > 0 for n in names)
