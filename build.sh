#!/bin/bash

set -e

if [ -z "$1" ]; then
  echo "Error: Version number not provided."
  echo "Usage: ./build.sh <version>"
  exit 1
fi

PACKAGE_NAME="tpp-df-bt-service"
VERSION=$1
STAGING_DIR="${PACKAGE_NAME}-${VERSION}"
DEBIAN_REVISION=1

# Clean up previous build
echo "Cleaning up previous build..."
rm -rf "${STAGING_DIR}"
rm -f "${PACKAGE_NAME}_${CURRENT_VERSION}-*.deb" # Use CURRENT_VERSION for cleanup

# Create staging directory structure
echo "Creating staging directory..."
mkdir -p "${STAGING_DIR}/DEBIAN"
mkdir -p "${STAGING_DIR}/etc/systemd/system"
mkdir -p "${STAGING_DIR}/etc/${PACKAGE_NAME}"
mkdir -p "${STAGING_DIR}/usr/lib/python3/dist-packages/tpp_df_bt_service"
mkdir -p "${STAGING_DIR}/usr/lib/python3/dist-packages/lib4relay"


# Copy application code
echo "Copying application code explicitly..."
cp "tpp_df_bt_service/__init__.py" "${STAGING_DIR}/usr/lib/python3/dist-packages/tpp_df_bt_service/"
cp "tpp_df_bt_service/__main__.py" "${STAGING_DIR}/usr/lib/python3/dist-packages/tpp_df_bt_service/"
cp "tpp_df_bt_service/service.py" "${STAGING_DIR}/usr/lib/python3/dist-packages/tpp_df_bt_service/"
cp "tpp_df_bt_service/web.py" "${STAGING_DIR}/usr/lib/python3/dist-packages/tpp_df_bt_service/"

# Copy dependencies
echo "Copying dependencies..."
cp -r "4relay/lib4relay/"* "${STAGING_DIR}/usr/lib/python3/dist-packages/lib4relay/"

# Install python dependencies
echo "Installing python dependencies..."
pip install --target="${STAGING_DIR}/usr/lib/python3/dist-packages" -r requirements.txt


# Copy packaging files and update version in the copied control file
echo "Copying packaging files and updating version..."
cp "debian/control" "${STAGING_DIR}/DEBIAN/control" # Copy first
sed -i "s/^Version: .*/Version: ${VERSION}/" "${STAGING_DIR}/DEBIAN/control" # Then modify in staging
cp "debian/postinst" "${STAGING_DIR}/DEBIAN/"
cp "debian/prerm" "${STAGING_DIR}/DEBIAN/"
chmod +x "${STAGING_DIR}/DEBIAN/postinst" "${STAGING_DIR}/DEBIAN/prerm"

# Copy service and config files
echo "Copying service and config files..."
cp "etc/systemd/system/tpp-df-bt.service" "${STAGING_DIR}/etc/systemd/system/"
cp "config.json" "${STAGING_DIR}/etc/${PACKAGE_NAME}/"

# Copy cron job and update script
echo "Copying cron job and update script..."
mkdir -p "${STAGING_DIR}/etc/cron.d"
cp "debian/tpp-df-bt-service-update" "${STAGING_DIR}/etc/cron.d/"
chmod 0644 "${STAGING_DIR}/etc/cron.d/tpp-df-bt-service-update"
mkdir -p "${STAGING_DIR}/usr/local/bin"
cp "update-tpp-df-bt-service.sh" "${STAGING_DIR}/usr/local/bin/"
chmod +x "${STAGING_DIR}/usr/local/bin/update-tpp-df-bt-service.sh"

# List staging directory contents
echo "Listing staging directory contents..."
ls -lR "${STAGING_DIR}"

# Build the package
echo "Building .deb package..."
dpkg-deb --build "${STAGING_DIR}"

# Rename the package to include the version
mv "${STAGING_DIR}.deb" "${PACKAGE_NAME}_${VERSION}-${DEBIAN_REVISION}_all.deb"

echo "Build complete: ${PACKAGE_NAME}_${VERSION}-${DEBIAN_REVISION}_all.deb"