#!/bin/bash

if [[ -z "$CREATE_FIRMWARE" ]]; then
  echo "Error: This script should be run within the create_firmware.sh environment."
  exit 1
fi

set -eo pipefail

echo ">> Installing PyYAML via pip3"
chroot_firmware.sh "$ROOTFS_DIR" /usr/bin/pip3 install pyyaml
