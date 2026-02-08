#!/usr/bin/env bash

GIT_URL=https://github.com/suchmememanyskill/filament-detect.git
GIT_SHA=8bab75a6511ae4c6caacafe165cde56cda57a4a3

if [[ -z "$CREATE_FIRMWARE" ]]; then
  echo "Error: This script should be run within the create_firmware.sh environment."
  exit 1
fi

set -eo pipefail

TARGET_DIR="$CACHE_DIR/filament-detect"
cache_git.sh "$TARGET_DIR" "$GIT_URL" "$GIT_SHA"

echo ">> Installing filament-detect..."
install -d "$ROOTFS_DIR/usr/local/bin/filament-detect"
cp -r "$TARGET_DIR/." "$ROOTFS_DIR/usr/local/bin/filament-detect/"
echo ">> filament-detect installation completed successfully."
