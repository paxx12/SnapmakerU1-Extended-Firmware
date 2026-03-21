#!/usr/bin/env bash

GIT_URL=https://github.com/justinh-rahb/panda-breath.git
GIT_SHA=638d44deb0f105dd0e5ec7977281718972e4d27d

if [[ -z "$CREATE_FIRMWARE" ]]; then
  echo "Error: This script should be run within the create_firmware.sh environment."
  exit 1
fi

set -eo pipefail

TARGET_DIR="$CACHE_DIR/panda-breath"
cache_git.sh "$TARGET_DIR" "$GIT_URL" "$GIT_SHA"

echo ">> Installing Panda Breath Klipper extras..."
install -Dm644 "$TARGET_DIR/panda_breath.py" \
  "$ROOTFS_DIR/usr/local/share/firmware-config/tweaks/klipper/panda_breath.py"
echo ">> Panda Breath installation completed successfully."
