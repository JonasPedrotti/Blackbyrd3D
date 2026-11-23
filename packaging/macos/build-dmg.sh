#!/usr/bin/env bash
# Build the macOS .app bundle and a drag-to-Applications .dmg.
# Run from this directory in a venv that has blackbyrd3d installed:
#   ./build-dmg.sh [path/to/venv/bin/python]
#
# Produces:  Blackbyrd3D-<version>-arm64.dmg
#
# The .app is UNSIGNED. Gatekeeper on the user's Mac will quarantine it;
# see the README for the right-click-Open / notarization follow-up.
set -euo pipefail
cd "$(dirname "$0")"

# Default to the repo's own venv. The system python3 has none of the runtime
# deps, and PyInstaller happily builds a 4 MB bundle out of it that only fails
# when someone opens it.
DEFAULT_PY="../../.venv/bin/python"
[ -x "$DEFAULT_PY" ] || DEFAULT_PY="python3"
PY="${1:-$DEFAULT_PY}"
VERSION="0.1.0"
APPNAME="Blackbyrd3D"
ARCH="$(uname -m)"
DMG="${APPNAME}-${VERSION}-${ARCH}.dmg"

echo "=== ensure pip (uv-created venvs ship without it) ==="
if ! "$PY" -m pip --version >/dev/null 2>&1; then
    "$PY" -m ensurepip --upgrade >/dev/null 2>&1 \
        || { command -v uv >/dev/null && uv pip install --python "$PY" pip; } \
        || { echo "ERROR: no pip and cannot bootstrap one"; exit 1; }
fi

echo "=== ensure build tools + real (non-editable) install ==="
"$PY" -m pip install --quiet pyinstaller
# setuptools stages the package into the repo's build/ and never takes
# anything out again, so a rename leaves the old tree there to be installed
# alongside the new one. `rm -rf build` further down clears PyInstaller's
# workspace in this directory, which is a different build/ entirely.
rm -rf ../../build
# PyInstaller cannot trace PEP 660 editable installs — install real files.
"$PY" -m pip install --quiet --force-reinstall --no-deps ../..

make_icns() {      # make_icns source.png name  ->  name.icns
    local iconset="$2.iconset"
    rm -rf "$iconset" "$2.icns"
    mkdir -p "$iconset"
    for sz in 16 32 128 256 512; do
        sips -z "$sz" "$sz"         "$1" --out "$iconset/icon_${sz}x${sz}.png"     >/dev/null
        sips -z $((sz*2)) $((sz*2)) "$1" --out "$iconset/icon_${sz}x${sz}@2x.png"  >/dev/null
    done
    iconutil -c icns "$iconset" -o "$2.icns"
    rm -rf "$iconset"
}

echo "=== generate byrd3d.icns and wyrm.icns ==="
make_icns byrd3d_icon.png byrd3d
make_icns wyrm_icon.png wyrm

echo "=== PyInstaller build ==="
# a failed run leaves a poisoned Analysis-00.toc that later runs reuse
rm -rf build dist
"$PY" -m PyInstaller --clean -y byrd3d.spec

APP="dist/${APPNAME}.app"
[ -d "$APP" ] || { echo "ERROR: $APP was not produced"; exit 1; }
# the .wyrm documents' icon, named in the spec's Info.plist
cp wyrm.icns "$APP/Contents/Resources/"

echo "=== bundle selftest (headless: Qt + OCCT + file I/O) ==="
# Delete last run's report first: a bundle that dies before writing one used
# to leave the previous release's file behind, and the grep below passed on it.
REPORT="${TMPDIR:-/tmp}/byrd3d-selftest.txt"
rm -f "$REPORT"
set +e
"$APP/Contents/MacOS/byrd3d" --selftest
STATUS=$?
set -e
[ -f "$REPORT" ] && cat "$REPORT"
[ "$STATUS" -eq 0 ] || { echo "ERROR: bundle exited $STATUS"; exit 1; }
grep -q "SELFTEST OK" "$REPORT" \
    || { echo "ERROR: bundle selftest failed"; exit 1; }

echo "=== assemble .dmg (drag onto Applications) ==="
STAGING="$(mktemp -d)"
cp -R "$APP" "$STAGING/"
ln -s /Applications "$STAGING/Applications"
rm -f "$DMG"
hdiutil create -volname "$APPNAME" -srcfolder "$STAGING" \
    -fs HFS+ -format UDZO -ov "$DMG" >/dev/null
rm -rf "$STAGING"

SIZE=$(du -h "$DMG" | cut -f1)
echo "DMG OK: $(pwd)/$DMG ($SIZE)"

# Put the venv back on the checkout. The install above is a copy of the
# source, so once the branch moves on, anything run out of that venv is
# quietly still the last build's code, which is a bad way to test a fix.
# The bundle is made by now, and the next build starts by replacing this
# with real files again, so PyInstaller never sees it.
"$PY" -m pip install --quiet --no-deps -e ../.. || true
