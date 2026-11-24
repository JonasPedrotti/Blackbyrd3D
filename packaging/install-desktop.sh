#!/usr/bin/env bash
# Install Blackbyrd3D into the user's desktop (Ubuntu/GNOME, no sudo):
# app in ~/Applications, launcher entry + icon in ~/.local/share, and a
# MIME types so .byrd and .wyrm files open with it from the file manager.
#
#   ./packaging/install-desktop.sh            # install the AppImage
#   ./packaging/install-desktop.sh --venv     # launch the dev checkout instead
#   ./packaging/install-desktop.sh --uninstall
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

APPS_DIR="$HOME/Applications"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
MIME_ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/mimetypes"
MIME_DIR="$HOME/.local/share/mime"
DESKTOP_FILE="$DESKTOP_DIR/blackbyrd3d.desktop"

refresh() {
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    update-mime-database "$MIME_DIR" 2>/dev/null || true
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" \
        2>/dev/null || true
}

remove_legacy() {
    # pre-rebrand names ("Serpentine"): drop them so search shows one app
    rm -f "$DESKTOP_DIR/serpentine.desktop" "$ICON_DIR/serpentine.png" \
          "$MIME_DIR/packages/serpentine.xml" \
          "$APPS_DIR/Serpentine.AppImage"
}

if [ "${1:-}" = "--uninstall" ]; then
    remove_legacy
    rm -f "$DESKTOP_FILE" "$ICON_DIR/blackbyrd3d.png" \
          "$MIME_ICON_DIR/application-x-blackbyrd3d.png" \
          "$MIME_ICON_DIR/application-x-blackbyrd3d-wyrm.png" \
          "$MIME_DIR/packages/blackbyrd3d.xml" \
          "$APPS_DIR/Blackbyrd3D.AppImage"
    refresh
    echo "Blackbyrd3D removed from the desktop."
    exit 0
fi

if [ "${1:-}" = "--venv" ]; then
    # run the working copy: picks up code changes without reinstalling
    EXEC_LINE="$ROOT/.venv/bin/python -m blackbyrd3d.app %F"
    [ -x "$ROOT/.venv/bin/python" ] || {
        echo "error: $ROOT/.venv/bin/python not found" >&2; exit 1; }
else
    APPIMAGE_SRC="$HERE/appimage/dist/Blackbyrd3D-$(uname -m).AppImage"
    [ -f "$APPIMAGE_SRC" ] || {
        echo "error: $APPIMAGE_SRC not found — run" \
             "packaging/appimage/build-appimage.sh first" >&2; exit 1; }
    mkdir -p "$APPS_DIR"
    install -m 755 "$APPIMAGE_SRC" "$APPS_DIR/Blackbyrd3D.AppImage"
    EXEC_LINE="$APPS_DIR/Blackbyrd3D.AppImage %F"
fi

remove_legacy
mkdir -p "$DESKTOP_DIR" "$ICON_DIR" "$MIME_ICON_DIR" "$MIME_DIR/packages"
install -m 644 "$HERE/appimage/blackbyrd3d.png" "$ICON_DIR/blackbyrd3d.png"
install -m 644 "$HERE/appimage/blackbyrd3d.png" \
    "$MIME_ICON_DIR/application-x-blackbyrd3d.png"
install -m 644 "$HERE/appimage/wyrm.png" \
    "$MIME_ICON_DIR/application-x-blackbyrd3d-wyrm.png"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=Blackbyrd3D
GenericName=NURBS Modeller
Comment=NURBS surface modeller for set design, architecture and product design
Exec=$EXEC_LINE
Icon=blackbyrd3d
Terminal=false
Categories=Graphics;3DGraphics;Engineering;
MimeType=application/x-blackbyrd3d;application/x-blackbyrd3d-wyrm;
Keywords=CAD;NURBS;3D;modelling;rhino;surface;drafting;
StartupWMClass=blackbyrd3d
EOF

cat > "$MIME_DIR/packages/blackbyrd3d.xml" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-blackbyrd3d">
    <comment>Blackbyrd3D 3D model</comment>
    <glob pattern="*.byrd"/>
    <icon name="application-x-blackbyrd3d"/>
  </mime-type>
  <mime-type type="application/x-blackbyrd3d-wyrm">
    <comment>Wyrm graph</comment>
    <glob pattern="*.wyrm"/>
    <icon name="application-x-blackbyrd3d-wyrm"/>
  </mime-type>
</mime-info>
EOF

refresh
# registration alone only adds an "Open With" entry; this makes it the default
xdg-mime default blackbyrd3d.desktop application/x-blackbyrd3d \
    application/x-blackbyrd3d-wyrm 2>/dev/null || true
command -v desktop-file-validate > /dev/null \
    && desktop-file-validate "$DESKTOP_FILE"

echo "Installed. Search for 'Blackbyrd3D' in Activities;"
echo ".byrd and .wyrm files now open with it from the file manager."
