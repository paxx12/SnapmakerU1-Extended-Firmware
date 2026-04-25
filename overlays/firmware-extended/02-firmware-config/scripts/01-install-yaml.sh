#!/usr/bin/env bash

if [[ -z "$CREATE_FIRMWARE" ]]; then
  echo "Error: This script should be run within the create_firmware.sh environment."
  exit 1
fi

set -eo pipefail

echo ">> Installing PyYAML via pip3"
cache_pip.sh "$ROOTFS_DIR" pyyaml
