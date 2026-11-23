"""What a packaged Blackbyrd3D can leave out.

cadquery-ocp requires the whole VTK wheel, about 300 MB, because OCP's
binary links a few VTK libraries for OCCT's VTK bridge. Nothing here ever
imports vtk, so only those libraries, and what they link in turn, have to
ship. VTK's own requirement brings matplotlib along, which nothing calls.

A library links another by file name, and that name is written into the
linking binary (ELF DT_NEEDED, a PE import, a Mach-O load command), so
finding a library's name in a binary's bytes finds the link. A name that
turns up for another reason only keeps a library that could have gone.

    python prune_bundle.py SITE_PACKAGES [--dry-run]

prunes an installed tree, as the AppImage build does, Qt's QML modules
and translations included; the PyInstaller specs call
`vtk_libraries_needed` to filter what they collect.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

_BINARY = re.compile(r"\.(so(\.[\d.]+)?|pyd|dll|dylib)$", re.IGNORECASE)
_LINK_NAME = re.compile(r"^(.+?\.(?:so|dll|dylib))", re.IGNORECASE)

# Plotting libraries VTK declares and nothing in the app calls.
UNUSED_PACKAGES = ("matplotlib", "mpl_toolkits", "contourpy", "kiwisolver",
                   "cycler")
# Qt's QML modules and its own translations: the app is widgets only and
# loads no translator.
UNUSED_QT = ("PySide6/Qt/qml", "PySide6/Qt/translations")


def _binaries(folder: Path):
    return [p for p in folder.rglob("*") if p.is_file() and _BINARY.search(p.name)]


def _ocp_roots(site: Path) -> list[Path]:
    roots = []
    for entry in site.iterdir():
        name = entry.name.lower()
        if name.startswith(("ocp", "cadquery_ocp")) and not name.endswith(
                (".dist-info", "proxy")):
            roots += _binaries(entry) if entry.is_dir() else (
                [entry] if _BINARY.search(entry.name) else [])
    return roots


def _vtk_pool(site: Path) -> list[Path]:
    pool = []
    for entry in site.iterdir():
        if entry.is_dir() and entry.name.lower().startswith(("vtk", ".vtk")) \
                and not entry.name.endswith(".dist-info"):
            pool += _binaries(entry)
    return pool


def vtk_libraries_needed(site) -> set[Path]:
    """The VTK libraries OCP links, directly or through each other."""
    site = Path(site)
    pool = {}
    for path in _vtk_pool(site):
        linked = _LINK_NAME.match(path.name)
        if linked:
            pool.setdefault(linked.group(1).encode(), []).append(path)
    keep: set[Path] = set()
    todo = _ocp_roots(site)
    seen: set[Path] = set()
    while todo:
        binary = todo.pop()
        if binary in seen:
            continue
        seen.add(binary)
        data = binary.read_bytes()
        for name, paths in pool.items():
            if name in data:
                for path in paths:
                    if path not in keep:
                        keep.add(path)
                        todo.append(path)
    return keep


def prune(site, dry_run: bool = False) -> int:
    """Remove the unused VTK libraries and packages from an installed
    tree; the bytes freed."""
    site = Path(site)
    keep = vtk_libraries_needed(site)
    if not keep:
        raise SystemExit("No VTK library linked from OCP was found; "
                         "refusing to prune a tree laid out differently")
    freed = 0
    doomed = [p for p in _vtk_pool(site) if p not in keep]
    for folder in (site / "vtkmodules",):
        if folder.is_dir():
            doomed += [p for p in folder.rglob("*")
                       if p.is_file() and p not in keep
                       and not _BINARY.search(p.name)]
    for name in UNUSED_PACKAGES + UNUSED_QT:
        folder = site / name
        if folder.is_dir():
            doomed += [p for p in folder.rglob("*") if p.is_file()]
    for path in doomed:
        freed += path.stat().st_size
        if not dry_run:
            path.unlink()
    if not dry_run:
        for name in UNUSED_PACKAGES + UNUSED_QT:
            shutil.rmtree(site / name, ignore_errors=True)
    return freed


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    if len(args) != 1:
        raise SystemExit(__doc__)
    freed = prune(args[0], dry_run="--dry-run" in sys.argv)
    print(f"Pruned {freed / 1e6:.0f} MB")
