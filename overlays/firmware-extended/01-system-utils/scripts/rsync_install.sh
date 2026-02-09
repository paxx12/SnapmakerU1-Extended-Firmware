#!/usr/bin/env bash

set -eo pipefail

if [[ -z "$CREATE_FIRMWARE" ]]; then
  echo "Error: This script should be run within the create_firmware.sh environment."
  exit 1
fi

cache_file.sh rsync "$CACHE_DIR/files/rsync.tar.gz" "$BUILD_DIR/rsync"

install -d "$ROOTFS_DIR/usr/local/bin"
install -m 755 "$BUILD_DIR/rsync/usr/local/bin/rsync" "$ROOTFS_DIR/usr/local/bin/rsync"
