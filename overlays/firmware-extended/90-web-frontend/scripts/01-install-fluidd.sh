#!/usr/bin/env bash

if [[ -z "$CREATE_FIRMWARE" ]]; then
  echo "Error: This script should be run within the create_firmware.sh environment."
  exit 1
fi

set -eo pipefail

rm -rf "$ROOTFS_DIR/home/lava/fluidd"

cache_file.sh fluidd "$CACHE_DIR/files/fluidd.zip" "$ROOTFS_DIR/home/lava/fluidd"
