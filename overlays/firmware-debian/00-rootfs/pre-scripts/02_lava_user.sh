#!/bin/bash

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"
ROOTFS_DIR="$(realpath "$1")"

set -e

if [[ ! -u "$ROOTFS_DIR/usr/bin/sudo" ]]; then
  echo ">> Setting setuid bit on /usr/bin/sudo..."
  "$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$ROOTFS_DIR" chmod u+s /usr/bin/sudo
fi

echo ">> Add user lava..."
"$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$ROOTFS_DIR" useradd -m -G sudo -s /bin/bash lava
"$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$ROOTFS_DIR" bash -c 'echo lava:snapmaker | chpasswd'
