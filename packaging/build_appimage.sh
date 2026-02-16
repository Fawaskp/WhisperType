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

# Create a simple SVG icon (placeholder — replace with real icon)
cat > "$APPDIR/whispertype.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <circle cx="32" cy="32" r="30" fill="#1E1E2E" stroke="#5B9BD5" stroke-width="3"/>
  <rect x="26" y="14" width="12" height="22" rx="6" fill="white"/>
  <path d="M20 32 a12 12 0 0 0 24 0" fill="none" stroke="white" stroke-width="2.5"/>
  <line x1="32" y1="44" x2="32" y2="52" stroke="white" stroke-width="2.5" stroke-linecap="round"/>
  <line x1="24" y1="52" x2="40" y2="52" stroke="white" stroke-width="2.5" stroke-linecap="round"/>
</svg>
SVG
cp "$APPDIR/whispertype.svg" "$APPDIR/usr/share/icons/hicolor/256x256/apps/"

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
ARCH=x86_64 "$APPIMAGETOOL" "$APPDIR" "$APPIMAGE"

# Clean up
rm -rf "$APPDIR"

echo "AppImage created: $APPIMAGE"
