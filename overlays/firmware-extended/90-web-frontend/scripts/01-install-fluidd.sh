#!/bin/bash

if [[ -z "$CREATE_FIRMWARE" ]]; then
  echo "Error: This script should be run within the create_firmware.sh environment."
  exit 1
fi

set -eo pipefail

VERSION=v1.36.2
URL=https://github.com/fluidd-core/fluidd/releases/download/$VERSION/fluidd.zip
SHA256=3f9dbe9ac5db51d1025a5737b207d83558c07cb0d7af34d3c5832c868fa72454
FILENAME=fluidd-$VERSION.zip

rm -rf "$ROOTFS_DIR/home/lava/fluidd"

cache_file.sh "$CACHE_DIR/$FILENAME" "$URL" "$SHA256" "$ROOTFS_DIR/home/lava/fluidd"
