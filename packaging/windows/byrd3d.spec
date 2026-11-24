# PyInstaller spec for the Windows build.
# Build (from this directory, in a venv with blackbyrd3d + pyinstaller):
#   pyinstaller --clean -y byrd3d.spec
import importlib.util
import sys
from pathlib import Path

from PyInstaller.utils.hooks import (collect_data_files, collect_dynamic_libs,
                                     copy_metadata)

sys.path.insert(0, str(Path(SPECPATH).parent))
from prune_bundle import vtk_libraries_needed  # noqa: E402

# OCP.pyd links against the VTK runtime shipped in the vtkmodules wheel;
# nothing imports vtk from Python, so collect the DLLs explicitly, and only
# the ones it links: the rest of VTK is some 200 MB nothing loads.
_site = Path(importlib.util.find_spec("OCP").origin).parents[1]
_linked = {p.name.lower() for p in vtk_libraries_needed(_site)}
vtk_bins = [b for b in collect_dynamic_libs("vtkmodules")
            if Path(b[0]).name.lower() in _linked]
# libE57 needs the Xerces XML runtime shipped beside its extension.
e57_bins = collect_dynamic_libs("pye57")

# ProductName/ProductVersion on the .exe, generated from the package version.
# SignPath enforces both at signing time; Windows shows them in Properties.
_mvi_path = Path(SPECPATH) / "make_version_info.py"
_mvi_spec = importlib.util.spec_from_file_location("make_version_info", _mvi_path)
make_version_info = importlib.util.module_from_spec(_mvi_spec)
_mvi_spec.loader.exec_module(make_version_info)
version_file = str(make_version_info.main())

a = Analysis(
    ["byrd3d_entry.py"],
    pathex=[],
    binaries=vtk_bins + e57_bins,
    # the metadata is where the bundled app reads its own version
    datas=collect_data_files("blackbyrd3d", includes=["examples/*.byrd",
                                                      "examples/*.wyrm"])
          + copy_metadata("blackbyrd3d"),
    hiddenimports=[],
    # A hook here replaces contrib's hook of the same name: hook-OpenGL.py
    # leaves out the DLLs PyOpenGL never loads on this Python.
    hookspath=[str(Path(SPECPATH) / "hooks")],
    excludes=[
        "tkinter",
        # VTK's requirement; only plotting add-ons of ezdxf and shapely
        # would import it, and nothing calls them
        "matplotlib",
        "vtk",
        "vtkmodules",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtQuick3D",
        "PySide6.QtPdf",
        "PySide6.QtCharts",
        "PySide6.QtMultimedia",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="byrd3d",
    icon="byrd3d.ico",
    version=version_file,        # ProductName/ProductVersion resource
    console=False,               # GUI app: no console window
    upx=False,                   # UPX corrupts Qt/OCCT DLLs
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="byrd3d",
    upx=False,
)
