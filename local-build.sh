#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

# Exit immediately if a command exits with a non-zero status.
set -e

# 1. Delete previous .deb files and staging folders
echo "Cleaning up previous builds..."
rm -f tpp-df-bt-service_*.deb
rm -rf tpp-df-bt-service-*

# 2. Increment the patch version
CURRENT_VERSION=$(grep "Version:" debian/control | awk '{print $2}')
MAJOR=$(echo $CURRENT_VERSION | cut -d. -f1)
MINOR=$(echo $CURRENT_VERSION | cut -d. -f2)
PATCH=$(echo $CURRENT_VERSION | cut -d. -f3)
NEW_PATCH=$((PATCH + 1))
NEW_VERSION="${MAJOR}.${MINOR}.${NEW_PATCH}"

echo "Incrementing version from ${CURRENT_VERSION} to ${NEW_VERSION}"

# Update debian/control
sed -i "s/Version: ${CURRENT_VERSION}/Version: ${NEW_VERSION}/g" debian/control

# Update README.md
sed -i "s/${CURRENT_VERSION}/${NEW_VERSION}/g" README.md

# 3. Build the service
echo "Building the service..."
./build.sh ${NEW_VERSION}

# Get the name of the newly built .deb file
DEB_FILE="tpp-df-bt-service_${NEW_VERSION}-1_all.deb"

# 4. Purge the existing service and clear logs
echo "Purging existing service..."
sudo apt-get purge -y tpp-df-bt-service || true # Use || true to prevent script from exiting if package is not installed

echo "Removing leftover directories to ensure a clean install..."
sudo rm -rf /etc/tpp-df-bt-service
sudo rm -rf /usr/lib/python3/dist-packages/tpp_df_bt_service

echo "Clearing journald logs..."
sudo journalctl --rotate && sudo journalctl --vacuum-time=1s

# 5. Install the new .deb file
echo "Installing the new service..."
sudo apt-get install -y "./${DEB_FILE}"

echo "Build and deployment complete. Please test the controllers."
