#!/bin/bash

if [[ -z "$CREATE_FIRMWARE" ]]; then
  echo "Error: This script should be run within the create_firmware.sh environment."
  exit 1
fi

set -eo pipefail

echo ">> Installing screen-apps"
make -C "$ROOT_DIR/deps/screen-apps" install DESTDIR="$ROOTFS_DIR"

echo ">> Installing Python dependencies for fb-http"
chroot_firmware.sh "$ROOTFS_DIR" /usr/bin/pip3 install $(cat "$ROOT_DIR/deps/screen-apps/apps/fb-http/requirements.txt")
