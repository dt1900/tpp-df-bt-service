#!/bin/bash

set -e

REPO="dt1900/tpp-df-bt-service"
PACKAGE_NAME="tpp-df-bt-service"

echo "Checking for new releases of $PACKAGE_NAME..."

# Get latest release data from GitHub API
LATEST_RELEASE=$(curl -s "https://api.github.com/repos/$REPO/releases/latest")

# Extract tag name and download URL
LATEST_VERSION=$(echo "$LATEST_RELEASE" | jq -r '.tag_name')
DEB_URL=$(echo "$LATEST_RELEASE" | jq -r '.assets[] | select(.name | endswith("_all.deb")) | .browser_download_url')

if [ -z "$LATEST_VERSION" ] || [ "$LATEST_VERSION" == "null" ]; then
    echo "Could not determine latest version. Exiting."
    exit 1
fi

if [ -z "$DEB_URL" ] || [ "$DEB_URL" == "null" ]; then
    echo "Could not find .deb asset in latest release. Exiting."
    exit 1
fi

# Get currently installed version
INSTALLED_VERSION_FULL=$(dpkg-query -W -f='${Version}' $PACKAGE_NAME 2>/dev/null || echo "0.0.0-0")
INSTALLED_VERSION=$(echo "$INSTALLED_VERSION_FULL" | cut -d'-' -f1)


echo "Latest version: $LATEST_VERSION"
echo "Installed version: $INSTALLED_VERSION"

# Compare versions
if [ "$LATEST_VERSION" == "$INSTALLED_VERSION" ]; then
    echo "$PACKAGE_NAME is up to date."
    exit 0
fi

echo "New version available. Downloading and installing..."

# Download the new package
TMP_DEB=$(mktemp)
wget -O "$TMP_DEB" "$DEB_URL"

# Purge the old package completely
# Use || true to prevent the script from failing if the package isn't installed
sudo apt-get purge -y $PACKAGE_NAME || true

# Explicitly remove leftover directories
echo "Removing leftover directories to ensure a clean install..."
sudo rm -rf /usr/lib/python3/dist-packages/tpp_df_bt_service

# Install the new package using apt-get to handle dependencies
sudo dpkg -i "$TMP_DEB"
sudo apt install -f

# Clean up
rm "$TMP_DEB"

echo "Update complete."
