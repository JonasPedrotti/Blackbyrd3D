"""Being the default application for .byrd and .wyrm files.

Each platform allows a different amount of help:

- Linux lets a user-level process do the whole job: register a MIME type
  and desktop entry, then `xdg-mime default`. No elevation, no dialog.
- Windows deliberately does not let applications set defaults (the
  UserChoice registry key is hash-protected), so the honest move is to
  open the Default Apps settings page where one click finishes it. The
  installer has already registered `Blackbyrd3D.Document`.
- macOS keeps the choice in Finder (Get Info -> Change All), so all that
  can be offered is the instruction.

The launch-time dialog lives in app.py; everything below is headless.
"""

from __future__ import annotations

import os
import subprocess
import sys

MIME = "application/x-blackbyrd3d"
WYRM_MIME = "application/x-blackbyrd3d-wyrm"
MIMES = (MIME, WYRM_MIME)
DESKTOP_ID = "blackbyrd3d.desktop"
APP_ICON = "blackbyrd3d"
_WIN_PROGID = "Blackbyrd3D.Document"


def exec_line() -> str:
    """How a file manager should start this very install."""
    appimage = os.environ.get("APPIMAGE")
    if appimage:
        return f"{appimage} %F"
    if getattr(sys, "frozen", False):
        return f"{sys.executable} %F"
    return f"{sys.executable} -m blackbyrd3d %F"


def desktop_entry(exec_cmd: str) -> str:
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Blackbyrd3D\n"
        "GenericName=NURBS Modeller\n"
        "Comment=NURBS surface modeller\n"
        f"Exec={exec_cmd}\n"
        "Icon=blackbyrd3d\n"
        "Terminal=false\n"
        "Categories=Graphics;3DGraphics;Engineering;\n"
        f"MimeType={MIME};{WYRM_MIME};\n"
        "Keywords=CAD;NURBS;3D;modelling;\n"
        "StartupWMClass=blackbyrd3d\n"
    )


def _icon_name(mime: str) -> str:
    """The freedesktop name of a MIME type's icon."""
    return mime.replace("/", "-")


def mime_xml() -> str:
    types = "".join(
        f'  <mime-type type="{mime}">\n'
        f"    <comment>{comment}</comment>\n"
        f'    <glob pattern="*.{ext}"/>\n'
        f'    <icon name="{_icon_name(mime)}"/>\n'
        "  </mime-type>\n"
        for mime, comment, ext in ((MIME, "Blackbyrd3D model", "byrd"),
                                   (WYRM_MIME, "Wyrm graph", "wyrm")))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<mime-info xmlns="http://www.freedesktop.org/standards/'
        'shared-mime-info">\n'
        f"{types}</mime-info>\n"
    )


def _data_home() -> str:
    return os.environ.get("XDG_DATA_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "share")


def status() -> str:
    """'default' | 'not_default' | 'unknown' — never raises."""
    if sys.platform.startswith("linux"):
        try:
            out = subprocess.run(
                ["xdg-mime", "query", "default", MIME],
                capture_output=True, text=True, timeout=5, check=False)
            return ("default" if out.stdout.strip() == DESKTOP_ID
                    else "not_default")
        except Exception:                                  # noqa: BLE001
            return "unknown"
    if sys.platform == "win32":
        return _status_windows()
    return "unknown"


def _status_windows() -> str:
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer"
            r"\FileExts\.byrd\UserChoice")
        progid, _ = winreg.QueryValueEx(key, "ProgId")
        return "default" if progid == _WIN_PROGID else "not_default"
    except OSError:
        pass                    # nobody chose in Settings: the class decides
    try:
        progid = winreg.QueryValue(winreg.HKEY_CLASSES_ROOT, ".byrd")
        return "default" if progid == _WIN_PROGID else "not_default"
    except OSError:
        return "not_default"


def should_offer(config) -> bool:
    """Ask on launch? Once, and never when the answer is already yes."""
    if config.get("file_assoc", "asked", default=False):
        return False
    return status() != "default"


def make_default() -> tuple[bool, str]:
    """Do as much as the platform permits. (something_happened, message)."""
    if sys.platform.startswith("linux"):
        return _make_default_linux()
    if sys.platform == "win32":
        try:
            os.startfile("ms-settings:defaultapps")
            return True, ("Settings opened: pick Blackbyrd3D for .byrd "
                          "and .wyrm to finish.")
        except Exception:                                  # noqa: BLE001
            return False, ("Open Settings > Apps > Default apps and pick "
                           "Blackbyrd3D for .byrd and .wyrm files.")
    if sys.platform == "darwin":
        return False, ("In Finder: Get Info on a .byrd or .wyrm file, "
                       "choose Blackbyrd3D under 'Open with', then "
                       "Change All.")
    return False, "No file association support on this platform."


def _paths() -> dict:
    share = _data_home()
    hicolor = os.path.join(share, "icons", "hicolor")
    size = os.path.join(hicolor, "256x256")
    return {
        "applications": os.path.join(share, "applications"),
        "desktop": os.path.join(share, "applications", DESKTOP_ID),
        "mime": os.path.join(share, "mime"),
        "mime_xml": os.path.join(share, "mime", "packages",
                                 "blackbyrd3d.xml"),
        "hicolor": hicolor,
        "icons": {
            APP_ICON: os.path.join(size, "apps", f"{APP_ICON}.png"),
            _icon_name(MIME): os.path.join(
                size, "mimetypes", f"{_icon_name(MIME)}.png"),
            _icon_name(WYRM_MIME): os.path.join(
                size, "mimetypes", f"{_icon_name(WYRM_MIME)}.png"),
        },
    }


def _run(cmd) -> bool:
    try:
        subprocess.run(cmd, capture_output=True, timeout=15, check=False)
        return True
    except Exception:                                      # noqa: BLE001
        return False


def _refresh(paths: dict) -> None:
    _run(["update-desktop-database", paths["applications"]])
    _run(["update-mime-database", paths["mime"]])
    _run(["gtk-update-icon-cache", "-f", "-t", paths["hicolor"]])


def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _write_icons(paths: dict) -> None:
    """The app's logo for it and its models, Wyrm's for graphs. Drawn by
    the app, so it needs one running; without, the files stay iconless."""
    try:
        from PySide6.QtGui import QGuiApplication
        if QGuiApplication.instance() is None:
            return
        from ..ui.brand import icon_pixmap
        from ..ui.icons import wyrm_icon
        app = icon_pixmap(256)
        wyrm = wyrm_icon().pixmap(256, 256)
    except Exception:                                      # noqa: BLE001
        return
    for name, pixmap in ((APP_ICON, app), (_icon_name(MIME), app),
                         (_icon_name(WYRM_MIME), wyrm)):
        path = paths["icons"][name]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        pixmap.save(path, "PNG")


def _desktop_exec(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("Exec="):
                    return line[len("Exec="):].strip()
    except OSError:
        return None
    return None


def _make_default_linux() -> tuple[bool, str]:
    paths = _paths()
    if not os.path.exists(paths["desktop"]):
        # install-desktop.sh may have written a richer entry; only a
        # missing one (bare AppImage download) gets this minimal stand-in
        _write(paths["desktop"], desktop_entry(exec_line()))
    _write(paths["mime_xml"], mime_xml())
    _write_icons(paths)
    _refresh(paths)
    if not all(_run(["xdg-mime", "default", DESKTOP_ID, mime])
               for mime in MIMES):
        return False, ("Could not run xdg-mime: set the default from "
                       "your file manager's 'Open With' menu instead.")
    return True, ("Blackbyrd3D is now the default app for .byrd and "
                  ".wyrm files.")


def follow_the_appimage() -> bool:
    """Point the desktop entry at the AppImage running now, if it moved.

    An AppImage is a file anyone can move, or replace with a newer one
    under another name, and the menu entry and double-clicked files then
    start nothing. Only an entry that starts an AppImage is rewritten, and
    only from an AppImage. True when it was."""
    if not (sys.platform.startswith("linux") and os.environ.get("APPIMAGE")):
        return False
    paths = _paths()
    current = _desktop_exec(paths["desktop"])
    wanted = exec_line()
    if current is None or current == wanted:
        return False
    if not current.endswith(".AppImage %F"):
        return False            # install-desktop.sh --venv runs a checkout
    _write(paths["desktop"], desktop_entry(wanted))
    _refresh(paths)
    return True


def remove_from_desktop() -> tuple[bool, str]:
    """Undo the Linux registration: menu entry, file types and icons."""
    if not sys.platform.startswith("linux"):
        return False, "Only Linux keeps a registration to remove."
    paths = _paths()
    for path in (paths["desktop"], paths["mime_xml"],
                 *paths["icons"].values()):
        try:
            os.remove(path)
        except OSError:
            pass
    _refresh(paths)
    return True, ("Blackbyrd3D is no longer in the app menu, and .byrd and "
                  ".wyrm files no longer open with it.")
