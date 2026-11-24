#!/usr/bin/env bash
# Build a Blackbyrd3D AppImage with python-appimage.
#
#   ./packaging/appimage/build-appimage.sh
#
# Produces Blackbyrd3D-<arch>.AppImage in packaging/appimage/dist, for the
# machine it runs on (x86_64 or aarch64): python-appimage cannot cross-build.
# Needs network access (PyPI wheels + a relocatable CPython runtime)
# and a few GB of scratch space. FUSE is not required to build.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
DIST="$HERE/dist"
PYVER="${BYRD3D_APPIMAGE_PYTHON:-3.12}"

# The glibc each architecture's PySide6 wheels need
ARCH="$(uname -m)"
case "$ARCH" in
    x86_64)  GLIBC=2_34 ;;
    aarch64) GLIBC=2_39 ;;
    *) echo "ERROR: no AppImage build for $ARCH" >&2; exit 1 ;;
esac

# recipe directory: its basename is the fallback app name; the .desktop
# Name= field (Blackbyrd3D) names the final AppImage.
RECIPE="$DIST/blackbyrd3d"
rm -rf "$RECIPE"
mkdir -p "$RECIPE"

cp "$HERE/blackbyrd3d.desktop" "$RECIPE/"
if [ -f "$HERE/blackbyrd3d.png" ]; then
    cp "$HERE/blackbyrd3d.png" "$RECIPE/"
else
    # placeholder icon so the recipe is self-sufficient
    python3 - "$RECIPE/blackbyrd3d.png" << 'PY'
import struct, sys, zlib
w = h = 64
row = b"\x00" + bytes((30, 160, 90, 255)) * w
raw = zlib.compress(row * h)
def chunk(t, d):
    c = struct.pack(">I", len(d)) + t + d
    return c + struct.pack(">I", zlib.crc32(t + d))
png = (b"\x89PNG\r\n\x1a\n"
       + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
       + chunk(b"IDAT", raw) + chunk(b"IEND", b""))
open(sys.argv[1], "wb").write(png)
PY
fi

# {{ python-executable }} is substituted by python-appimage at build time.
# -P: without it `-m` puts the launch directory first on sys.path, so starting
# the AppImage from anywhere containing a blackbyrd3d/ folder — a checkout,
# say — runs that code instead of the bundled package, silently.
cat > "$RECIPE/entrypoint.sh" << 'EOF'
{{ python-executable }} -P -m blackbyrd3d "$@"
EOF

# no spaces: python-appimage word-splits requirement lines when invoking pip
printf 'blackbyrd3d@file://%s\n' "$ROOT" > "$RECIPE/requirements.txt"

# Pin everything to uv.lock, the versions CI tested. Unpinned, pip takes
# whatever PyPI has newest that day: the AppImage once shipped Qt 6.12 while
# CI still ran 6.11, and a dock bug only Qt 6.12 had could not be reproduced
# anywhere else. The lock is resolved for this one target (CPython $PYVER on
# $ARCH Linux, with the glibc PySide6's wheels need), which settles every
# marker. It goes to pip as a constraints file rather than as requirements:
# python-appimage installs requirement lines one at a time, so pins listed
# there arrive after our package has already pulled in the newest of
# everything, and pip refuses the downgrades. A constraint holds at every
# step, transitive dependencies included.
if command -v uv > /dev/null 2>&1; then
    PINS="$DIST/pins"
    mkdir -p "$PINS"
    ( cd "$ROOT" && uv export --frozen --no-dev --no-hashes --no-emit-project \
        --no-annotate --no-header ) > "$PINS/locked.txt"
    uv pip compile "$PINS/locked.txt" --python-version "$PYVER" \
        --python-platform "$ARCH-manylinux_$GLIBC" --no-deps --no-header \
        --no-annotate -q -o "$PINS/pinned.txt"
    export PIP_CONSTRAINT="$PINS/pinned.txt"
    echo "Pinned to uv.lock: $(wc -l < "$PINS/pinned.txt") packages"
else
    echo "WARNING: uv not found, so the AppImage takes PyPI's newest" \
         "versions rather than the ones uv.lock pins" >&2
fi

if command -v uvx > /dev/null 2>&1; then
    BUILDER=(uvx python-appimage)
else
    python3 -m pip install --user --upgrade python-appimage
    BUILDER=(python3 -m python_appimage)
fi

# pip keys its wheel cache on name+version, and our version only moves at
# release time — so without this a rebuild between releases quietly reuses the
# wheel from the last one and bundles yesterday's code while the source tree
# looks correct. Only ours: the third-party wheels are worth caching.
CACHE="${PIP_CACHE_DIR:-$HOME/.cache/pip}/wheels"
if [ -d "$CACHE" ]; then
    find "$CACHE" -name 'blackbyrd3d-*.whl' -delete
fi

# setuptools copies the packages it is told to build into build/lib and never
# takes anything out again, but the wheel is zipped from whatever it finds
# there, so a renamed or deleted package would ride along in every wheel. Staging is pure copying for a pure-Python package; rebuilding
# it from scratch costs a second and removes the whole class of problem.
rm -rf "$ROOT/build"

cd "$DIST"
"${BUILDER[@]}" build app --python-version "$PYVER" "$RECIPE"

BUILT="$(ls "$DIST"/Blackbyrd3D-*.AppImage 2>/dev/null | head -1)"
ls -lh "$BUILT"

# Inspect the complete bundle before it can replace the desktop-installed copy,
# and take out what it carries for nothing: most of VTK and matplotlib, which
# cadquery-ocp drags in, and Qt's QML and translations (see prune_bundle.py).
# Besides catching stale package names, running the real application through
# the bundled Python, after the pruning, catches incompatible binary wheels and
# missing libraries, a library pruned that was needed among them.
if [ -n "$BUILT" ]; then
    PROBE="$(mktemp -d)"
    trap 'rm -rf "$PROBE"' EXIT
    ( cd "$PROBE" && "$BUILT" --appimage-extract > /dev/null 2>&1 )
    SITE_PACKAGES="$PROBE/squashfs-root/opt/python$PYVER/lib/python$PYVER/site-packages"
    STOWAWAYS="$(
        for PACKAGE in "$SITE_PACKAGES"/blackbyrd*; do
            [ -f "$PACKAGE/__init__.py" ] || continue
            basename "$PACKAGE"
        done | sort -u | grep -vx 'blackbyrd3d' || true
    )"
    if [ -n "$STOWAWAYS" ]; then
        echo "ERROR: the bundle ships top-level packages we did not intend:" >&2
        echo "$STOWAWAYS" | sed 's/^/  /' >&2
        echo "Stale setuptools staging, or a rename that left a tree behind." >&2
        exit 1
    fi

    python3 "$HERE/../prune_bundle.py" "$SITE_PACKAGES"

    QT_QPA_PLATFORM=offscreen "$PROBE/squashfs-root/usr/bin/python$PYVER" -P - << 'PY'
import blackbyrd3d.app
import platform
if platform.machine() != "aarch64":  # left out there, see pyproject
    import pye57  # Load libE57 and its bundled Xerces runtime before handoff.
import openskp, mapbox_earcut, shapely.geometry  # SketchUp's reader (#42).
from PySide6.QtWidgets import QApplication
app = QApplication([])
from blackbyrd3d.core import geometry as g
from blackbyrd3d.core.tessellate import tessellate
from blackbyrd3d.core.text_object import TextShape
# OCP loads the VTK libraries it links as it is imported; meshing a boolean
# and a line of lettering exercises the kernel the app actually uses.
solid = g.boolean_difference(g.make_box((0, 0, 0), 10, 10, 10),
                             g.make_sphere((0, 0, 0), 6))
assert len(tessellate(solid).triangles)
assert len(tessellate(TextShape("Ag", 5.)).triangles)
PY

    # Importing is not starting: show the window and let it handle its first
    # events, where the AppImage once crashed right after the splash. Linux's
    # offscreen platform has no OpenGL, so this needs a display: a virtual
    # one where xvfb-run exists, else the desktop the build runs on.
    WINDOW_CHECK=(env)
    if command -v xvfb-run > /dev/null 2>&1; then
        WINDOW_CHECK=(xvfb-run -a env QT_QPA_PLATFORM=xcb)
    elif [ -z "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
        WINDOW_CHECK=()
        echo "WARNING: no display and no xvfb-run, so the main window" \
             "was not started" >&2
    fi
    if [ ${#WINDOW_CHECK[@]} -gt 0 ]; then
        BYRD3D_NO_RPC=1 "${WINDOW_CHECK[@]}" \
            "$PROBE/squashfs-root/usr/bin/python$PYVER" -P -X faulthandler - << 'PY'
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
app = QApplication([])
from blackbyrd3d.app import MainWindow
window = MainWindow()
window.show()
QTimer.singleShot(3000, app.quit)
app.exec()
window.close()
PY
    fi
    echo "Packaged application check passed"

    # python-appimage packed the bundle before it was pruned: pack it again.
    TOOL="$(command -v appimagetool || true)"
    if [ -z "$TOOL" ]; then
        TOOL="$DIST/appimagetool-$ARCH.AppImage"
        [ -x "$TOOL" ] || {
            curl -fsSL -o "$TOOL" "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARCH.AppImage"
            chmod +x "$TOOL"
        }
    fi
    # The extracted tree comes out 0700, and packed that way only the user
    # who built the AppImage could run it.
    chmod -R a+rX "$PROBE/squashfs-root"
    APPIMAGE_EXTRACT_AND_RUN=1 ARCH="$ARCH" "$TOOL" --no-appstream \
        "$PROBE/squashfs-root" "$BUILT.pruned" > /dev/null
    mv "$BUILT.pruned" "$BUILT"
    ls -lh "$BUILT"
fi

# Keep the desktop-installed copy (what the dock/launcher runs) in sync
# with this build, so a rebuild is immediately live and never drifts from
# dist/. Only touches an existing install; skip with BYRD3D_NO_INSTALL_REFRESH=1.
INSTALLED="$HOME/Applications/Blackbyrd3D.AppImage"
if [ -n "$BUILT" ] && [ -f "$INSTALLED" ] \
        && [ "${BYRD3D_NO_INSTALL_REFRESH:-}" != "1" ]; then
    install -m 755 "$BUILT" "$INSTALLED"
    echo "Refreshed installed copy: $INSTALLED"
fi
