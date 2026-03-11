#!/usr/bin/env bash
# Build an Arch Linux package (.pkg.tar.zst) for WhisperType.
#
# Prerequisites:
#   pacman -S --needed base-devel python python-pip python-setuptools python-wheel
#
# Usage:
#   bash packaging/build_archlinux.sh
#
# Output:
#   dist/whispertype-<version>-<pkgrel>-x86_64.pkg.tar.zst

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"

PKGNAME="whispertype"
PKGVER="1.0.0"

# Read version from pyproject.toml if possible
if command -v python3 &>/dev/null; then
    _ver=$(python3 -c "
import re, pathlib
t = pathlib.Path('${ROOT}/pyproject.toml').read_text()
m = re.search(r'version\s*=\s*\"([^\"]+)\"', t)
print(m.group(1) if m else '')
" 2>/dev/null || true)
    [ -n "$_ver" ] && PKGVER="$_ver"
fi

BUILDDIR="$(mktemp -d)"
TARBALL="${PKGNAME}-${PKGVER}.tar.gz"

trap 'rm -rf "$BUILDDIR"' EXIT

echo "==> Creating source tarball (v${PKGVER})..."
tar -czf "${BUILDDIR}/${TARBALL}" \
    --transform="s,^\.,${PKGNAME}-${PKGVER}," \
    --exclude='.git' \
    --exclude='dist' \
    --exclude='build' \
    --exclude='voice_app/venv' \
    --exclude='__pycache__' \
    --exclude='*.egg-info' \
    -C "$ROOT" .

echo "==> Preparing PKGBUILD..."
cp "${SCRIPT_DIR}/PKGBUILD" "${BUILDDIR}/PKGBUILD"

# Update pkgver in PKGBUILD to match pyproject.toml
sed -i "s/^pkgver=.*/pkgver=${PKGVER}/" "${BUILDDIR}/PKGBUILD"

echo "==> Building package..."
cd "$BUILDDIR"
makepkg -sf --noconfirm

echo "==> Copying package to dist/..."
mkdir -p "${ROOT}/dist"
cp "${BUILDDIR}"/*.pkg.tar.zst "${ROOT}/dist/"

PKG=$(ls "${ROOT}/dist/${PKGNAME}"-*.pkg.tar.zst 2>/dev/null | head -1)
echo "Package created: ${PKG}"
