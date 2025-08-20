#!/bin/bash

set -e

PACKAGE_NAME="tpp-df-bt-service"
VERSION="1.0.0"
STAGING_DIR="${PACKAGE_NAME}-${VERSION}"

# Clean up previous build
echo "Cleaning up previous build..."
rm -rf "${STAGING_DIR}"
rm -f "${PACKAGE_NAME}_${VERSION}_*.deb"

# Create staging directory structure
echo "Creating staging directory..."
mkdir -p "${STAGING_DIR}/DEBIAN"
mkdir -p "${STAGING_DIR}/etc/systemd/system"
mkdir -p "${STAGING_DIR}/etc/${PACKAGE_NAME}"
mkdir -p "${STAGING_DIR}/usr/lib/python3/dist-packages/${PACKAGE_NAME}"
mkdir -p "${STAGING_DIR}/usr/lib/python3/dist-packages/lib4relay"
mkdir -p "${STAGING_DIR}/usr/lib/python3/dist-packages/pyPS4Controller"


# Copy application code
echo "Copying application code..."
cp -r "tpp_df_bt_service/"* "${STAGING_DIR}/usr/lib/python3/dist-packages/${PACKAGE_NAME}/"

# Copy dependencies
echo "Copying dependencies..."
cp -r "4relay/lib4relay/"* "${STAGING_DIR}/usr/lib/python3/dist-packages/lib4relay/"
cp -r "venv/lib/python3.11/site-packages/pyPS4Controller/"* "${STAGING_DIR}/usr/lib/python3/dist-packages/pyPS4Controller/"


# Copy packaging files
echo "Copying packaging files..."
cp "debian/control" "${STAGING_DIR}/DEBIAN/"
cp "debian/postinst" "${STAGING_DIR}/DEBIAN/"
cp "debian/prerm" "${STAGING_DIR}/DEBIAN/"
chmod +x "${STAGING_DIR}/DEBIAN/postinst" "${STAGING_DIR}/DEBIAN/prerm"

# Copy service and config files
echo "Copying service and config files..."
cp "etc/systemd/system/tpp-df-bt.service" "${STAGING_DIR}/etc/systemd/system/"
cp "config.json" "${STAGING_DIR}/etc/${PACKAGE_NAME}/"


# Build the package
echo "Building .deb package..."
dpkg-deb --build "${STAGING_DIR}"

echo "Build complete: ${STAGING_DIR}.deb"

