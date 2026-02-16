#!/usr/bin/env bash
# Build a Linux AppImage from the PyInstaller output.
#
# Prerequisites:
#   pip install pyinstaller
#   pyinstaller packaging/whispertype_linux.spec --noconfirm
#   wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
#   chmod +x appimagetool-x86_64.AppImage
#
# Usage:
#   bash packaging/build_appimage.sh
#
# Output:
#   dist/WhisperType.AppImage

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
DIST="$ROOT/dist/WhisperType"
APPDIR="$ROOT/dist/WhisperType.AppDir"
APPIMAGE="$ROOT/dist/WhisperType.AppImage"

if [ ! -d "$DIST" ]; then
    echo "Error: $DIST not found."
    echo "Run:  pyinstaller packaging/whispertype_linux.spec --noconfirm"
    exit 1
fi

# Clean previous AppDir
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"

# Copy PyInstaller output
cp -R "$DIST"/* "$APPDIR/usr/bin/"

# Create .desktop file
cat > "$APPDIR/whispertype.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=WhisperType
Comment=Voice-to-text overlay application
Exec=WhisperType
Icon=whispertype
Categories=Utility;Audio;
Terminal=false
DESKTOP
cp "$APPDIR/whispertype.desktop" "$APPDIR/usr/share/applications/"

# Copy app icon
cp "$ROOT/packaging/icon.png" "$APPDIR/whispertype.png"
cp "$ROOT/packaging/icon.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/whispertype.png"

# Create AppRun
cat > "$APPDIR/AppRun" <<'APPRUN'
#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/WhisperType" "$@"
APPRUN
chmod +x "$APPDIR/AppRun"

# Build AppImage
APPIMAGETOOL="${APPIMAGETOOL:-appimagetool-x86_64.AppImage}"
if ! command -v "$APPIMAGETOOL" &>/dev/null; then
    if [ -f "$ROOT/$APPIMAGETOOL" ]; then
        APPIMAGETOOL="$ROOT/$APPIMAGETOOL"
    else
        echo "Error: appimagetool not found."
        echo "Download from: https://github.com/AppImage/AppImageKit/releases"
        exit 1
    fi
fi

rm -f "$APPIMAGE"
ARCH=x86_64 "$APPIMAGETOOL" --appimage-extract-and-run "$APPDIR" "$APPIMAGE"

# Clean up
rm -rf "$APPDIR"

echo "AppImage created: $APPIMAGE"
