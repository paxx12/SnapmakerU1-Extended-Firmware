#!/usr/bin/env bash

set -eo pipefail

if [[ -z "$CREATE_FIRMWARE" ]]; then
  echo "Error: This script should be run within the create_firmware.sh environment."
  exit 1
fi

TARGET_FILE="$CACHE_DIR/files/opkg"
cache_file.sh entware "$TARGET_FILE"

echo ">> Installing latest Entware installer"
install -d "$ROOTFS_DIR/usr/local/bin"
install -m 755 "$TARGET_FILE" "$ROOTFS_DIR/usr/local/bin/opkg"
