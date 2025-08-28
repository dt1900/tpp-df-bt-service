#!/bin/bash

set -e

if [ -z "$1" ]; then
  echo "Error: Version number not provided."
  echo "Usage: ./update-version.sh <new_version>"
  exit 1
fi

NEW_VERSION=$1

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Get current version from debian/control for replacement
CURRENT_VERSION=$(grep "Version:" "${PROJECT_ROOT}/debian/control" | awk '{print $2}')

echo "Updating version from ${CURRENT_VERSION} to ${NEW_VERSION}"

# Update debian/control
sed -i "s/Version: ${CURRENT_VERSION}/Version: ${NEW_VERSION}/g" "${PROJECT_ROOT}/debian/control"

# Update README.md
sed -i "s/${CURRENT_VERSION}/${NEW_VERSION}/g" "${PROJECT_ROOT}/README.md"

# Update config.json
sed -i "s/\"version\": \"${CURRENT_VERSION}\"/\"version\": \"${NEW_VERSION}\"/g" "${PROJECT_ROOT}/config.json"

echo "Version updated to ${NEW_VERSION} in debian/control, README.md, and config.json."

