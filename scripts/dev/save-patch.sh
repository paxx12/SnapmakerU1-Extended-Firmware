#!/bin/bash

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 <overlay> <patch-name> <file-changed-paths>"
  echo "Example: $0 camera-native 02-disable-wlan-power-save /path/to/02-disable-wlan-power-save.patch"
  exit 1
fi

set -xeo pipefail

if [[ ! -d tmp/extracted/rootfs.original ]]; then
  unsquashfs -d tmp/extracted/rootfs.original tmp/extracted/rk-unpacked/rootfs.img
fi

OVERLAY_NAME="$1"
PATCH_NAME="$2"
shift 2

mkdir -p "overlays/$OVERLAY_NAME/patches"

for patch_file; do
  diff \
    --label "a/$patch_file" \
    --label "b/$patch_file" \
    -uNr tmp/extracted/{rootfs.original,rootfs}/"$patch_file"
done > "overlays/$OVERLAY_NAME/patches/$PATCH_NAME.patch"
