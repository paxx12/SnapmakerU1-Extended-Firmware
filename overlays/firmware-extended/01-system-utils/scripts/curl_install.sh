#!/usr/bin/env bash

set -eo pipefail

if [[ -z "$CREATE_FIRMWARE" ]]; then
  echo "Error: This script should be run within the create_firmware.sh environment."
  exit 1
fi

cache_file.sh curl "$CACHE_DIR/files/curl.tar.xz" "$BUILD_DIR/curl"

install -d "$ROOTFS_DIR/usr/local/bin"
install -m 755 "$BUILD_DIR/curl/curl" "$ROOTFS_DIR/usr/local/bin/curl"
