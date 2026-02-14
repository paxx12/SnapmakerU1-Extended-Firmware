#!/usr/bin/env bash

GIT_URL=https://github.com/paxx12/klipper-router.git
GIT_SHA=c350612121cb71e914ecbcff0523a46cfab07e36

if [[ -z "$CREATE_FIRMWARE" ]]; then
  echo "Error: This script should be run within the create_firmware.sh environment."
  exit 1
fi

set -eo pipefail

TARGET_DIR="$CACHE_DIR/klipper-router"
cache_git.sh "$TARGET_DIR" "$GIT_URL" "$GIT_SHA"

install -m 0755 "$TARGET_DIR/src/klipper_router.py" "$1/usr/local/sbin/klipper-routerd"

# Optional reference copy for future config/macro syncing
mkdir -p "$1/usr/local/share/firmware-config/router/includes"
install -m 0644 "$TARGET_DIR/includes/router_api.cfg" "$1/usr/local/share/firmware-config/router/includes/router_api.cfg"

echo ">> klipper-router installed successfully"
