#!/usr/bin/env bash

if [[ -z "$CREATE_FIRMWARE" ]]; then
  echo "Error: This script should be run within the create_firmware.sh environment."
  exit 1
fi

set -eo pipefail

TARGET_DIR="$CACHE_DIR/repos/timelapse-recovery"
cache_git.sh timelapse-recovery "$TARGET_DIR"

echo ">> Installing Timelapse Recovery Tool..."
install -m 755 -d "$ROOTFS_DIR/usr/local/bin"
install -m 755 "$TARGET_DIR/fix_timelapse.py" "$ROOTFS_DIR/usr/local/bin/fix_timelapse"
