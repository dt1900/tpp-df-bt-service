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

# Install the new package
sudo dpkg -i "$TMP_DEB"

# Clean up
rm "$TMP_DEB"

echo "Update complete."
