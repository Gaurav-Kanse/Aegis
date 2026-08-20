#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

VERSION="0.1.0"
PKG_NAME="aegis"
ARCHIVE_NAME="${PKG_NAME}-${VERSION}"

echo "[aegis-build] Building Aegis v${VERSION} RPM package..."

# Navigate to workspace root
cd "$ROOT_DIR"

# Ensure dist output directory exists
mkdir -p "$ROOT_DIR/dist"

# Setup local rpmbuild structure
RPMBUILD_DIR="${HOME}/rpmbuild"
mkdir -p "$RPMBUILD_DIR"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}

# Create source archive
echo "[aegis-build] Creating source tarball ${ARCHIVE_NAME}.tar.gz..."
TAR_TMP=$(mktemp -d)
mkdir -p "$TAR_TMP/$ARCHIVE_NAME"

# Copy project files (excluding git and build artifacts)
cp -r aegis packaging systemd polkit tests README.md LICENSE pyproject.toml setup.py "$TAR_TMP/$ARCHIVE_NAME/"

tar -czf "$RPMBUILD_DIR/SOURCES/${ARCHIVE_NAME}.tar.gz" -C "$TAR_TMP" "$ARCHIVE_NAME"
rm -rf "$TAR_TMP"

# Copy spec file
cp "$ROOT_DIR/packaging/fedora/aegis.spec" "$RPMBUILD_DIR/SPECS/"

# Execute rpmbuild
echo "[aegis-build] Running rpmbuild..."
rpmbuild -ba "$RPMBUILD_DIR/SPECS/aegis.spec"

# Find and copy built RPM to dist/
BUILT_RPM=$(find "$RPMBUILD_DIR/RPMS" -name "${PKG_NAME}-${VERSION}*.rpm" | head -n 1)

if [ -f "$BUILT_RPM" ]; then
    cp "$BUILT_RPM" "$ROOT_DIR/dist/"
    FINAL_RPM="$ROOT_DIR/dist/$(basename "$BUILT_RPM")"
    echo "[aegis-build] Successfully built RPM: $FINAL_RPM"
    
    # Generate SHA256 sum
    cd "$ROOT_DIR/dist"
    sha256sum "$(basename "$BUILT_RPM")" > SHA256SUMS
    echo "[aegis-build] SHA256 checksum generated in dist/SHA256SUMS"
else
    echo "[aegis-build] Error: Built RPM not found in $RPMBUILD_DIR/RPMS"
    exit 1
fi
