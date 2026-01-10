#!/bin/bash

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"
ROOTFS_DIR="$(realpath "$1")"
ORG_ROOTFS_DIR="${ROOTFS_DIR}.org"

set -e

"$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$ROOTFS_DIR" apt-get purge -y \
  build-essential \
  cpp-14-aarch64-linux-gnu \
  gcc-14-aarch64-linux-gnu \
  g++-14-aarch64-linux-gnu \
  libpython3.13-dev \
  libgcc-14-dev \
  vim-runtime \
  git

rm -rf "$ROOTFS_DIR/var/cache/apt/"
rm -rf "$ROOTFS_DIR/var/lib/apt/lists/"
find "$ROOTFS_DIR/var/log" -type f -delete
rm -rf "$ROOTFS_DIR/tmp/"*
rm -rf "$ROOTFS_DIR/usr/share/locale/"
rm -rf "$ROOTFS_DIR/etc/machine-id"
rm -rf "$ROOTFS_DIR/root/.cache/"
