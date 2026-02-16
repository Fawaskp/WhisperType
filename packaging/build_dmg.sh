#!/usr/bin/env bash
# Build a macOS DMG from the PyInstaller .app bundle.
#
# Prerequisites:
#   pip install pyinstaller
#   pyinstaller packaging/whispertype_macos.spec --noconfirm
#
# Usage:
#   bash packaging/build_dmg.sh
#
# Output:
#   dist/WhisperType.dmg

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
APP_PATH="$ROOT/dist/WhisperType.app"
DMG_PATH="$ROOT/dist/WhisperType.dmg"
VOLUME_NAME="WhisperType"

if [ ! -d "$APP_PATH" ]; then
    echo "Error: $APP_PATH not found."
    echo "Run:  pyinstaller packaging/whispertype_macos.spec --noconfirm"
    exit 1
fi

# Remove old DMG if present
rm -f "$DMG_PATH"

# Create a temporary directory for DMG contents
STAGING="$ROOT/dist/_dmg_staging"
rm -rf "$STAGING"
mkdir -p "$STAGING"

cp -R "$APP_PATH" "$STAGING/"

# Create a symlink to /Applications for drag-and-drop install
ln -s /Applications "$STAGING/Applications"

# Build the DMG
hdiutil create \
    -volname "$VOLUME_NAME" \
    -srcfolder "$STAGING" \
    -ov -format UDZO \
    "$DMG_PATH"

# Clean up
rm -rf "$STAGING"

echo "DMG created: $DMG_PATH"
