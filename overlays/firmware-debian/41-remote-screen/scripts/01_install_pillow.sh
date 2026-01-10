#!/bin/bash

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

set -eo pipefail

echo ">> Installing Pillow for JPEG support"
"$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$1" /usr/bin/pip3 install --break-system-packages Pillow
