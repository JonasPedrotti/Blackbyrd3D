# PyInstaller spec for the macOS .app bundle (Apple Silicon / arm64).
# Build (from this directory, in a venv with blackbyrd3d + pyinstaller):
#   pyinstaller --clean -y byrd3d.spec
# Produces dist/Blackbyrd3D.app.  See build-dmg.sh for the full flow.
import importlib.util
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

sys.path.insert(0, str(Path(SPECPATH).parent))
from prune_bundle import vtk_libraries_needed  # noqa: E402

# OCP.so links the OCCT runtime via @loader_path/.dylibs/libTK*.dylib, and
# that runtime in turn pulls in the VTK dylibs from the vtkmodules wheel.
# Nothing imports either from Python, so collect both explicitly, VTK only
# as far as OCP links it: the rest is some 200 MB nothing loads.
_site = Path(importlib.util.find_spec("OCP").origin).parents[1]
_linked = {p.name.lower() for p in vtk_libraries_needed(_site)}
binaries = collect_dynamic_libs("OCP") + [
    b for b in collect_dynamic_libs("vtkmodules")
    if Path(b[0]).name.lower() in _linked]
# libE57 needs the Xerces XML runtime shipped beside its extension.
binaries += collect_dynamic_libs("pye57")

a = Analysis(
    ["byrd3d_entry.py"],
    pathex=[],
    binaries=binaries,
    datas=collect_data_files("blackbyrd3d", includes=["examples/*.byrd",
                                                      "examples/*.wyrm"]),
    hiddenimports=[],
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
    console=False,               # GUI app: no terminal
    upx=False,                   # UPX corrupts Qt/OCCT libraries
    target_arch=None,            # native (arm64 on Apple Silicon)
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="byrd3d",
    upx=False,
)
app = BUNDLE(
    coll,
    name="Blackbyrd3D.app",
    icon="byrd3d.icns",
    bundle_identifier="com.jonaspedrotti.blackbyrd3d",
    version="0.1.0",
    info_plist={
        "CFBundleName": "Blackbyrd3D",
        "CFBundleDisplayName": "Blackbyrd3D",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleVersion": "0.1.0",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "14.0",
        "LSApplicationCategoryType": "public.app-category.graphics-design",
        "NSHumanReadableCopyright": "MIT License · Jonas Pedrotti",
        # Claim .byrd so Finder offers (and can default to) this app.
        # The path arrives as a QFileOpenEvent — see app.FileOpenRelay.
        # The icons are the app's own and wyrm.icns, which build-dmg.sh
        # puts into Contents/Resources.
        "CFBundleDocumentTypes": [{
            "CFBundleTypeName": "Blackbyrd3D model",
            "CFBundleTypeRole": "Editor",
            "LSHandlerRank": "Owner",
            "LSItemContentTypes": ["com.jonaspedrotti.blackbyrd3d.byrd"],
            "CFBundleTypeIconFile": "byrd3d.icns",
        }, {
            "CFBundleTypeName": "Wyrm graph",
            "CFBundleTypeRole": "Editor",
            "LSHandlerRank": "Owner",
            "LSItemContentTypes": ["com.jonaspedrotti.blackbyrd3d.wyrm"],
            "CFBundleTypeIconFile": "wyrm.icns",
        }],
        "UTExportedTypeDeclarations": [{
            "UTTypeIdentifier": "com.jonaspedrotti.blackbyrd3d.byrd",
            "UTTypeDescription": "Blackbyrd3D model",
            "UTTypeConformsTo": ["public.data"],
            "UTTypeIconFile": "byrd3d.icns",
            "UTTypeTagSpecification": {
                "public.filename-extension": ["byrd"],
            },
        }, {
            "UTTypeIdentifier": "com.jonaspedrotti.blackbyrd3d.wyrm",
            "UTTypeDescription": "Wyrm graph",
            "UTTypeConformsTo": ["public.data"],
            "UTTypeIconFile": "wyrm.icns",
            "UTTypeTagSpecification": {
                "public.filename-extension": ["wyrm"],
            },
        }],
    },
)
