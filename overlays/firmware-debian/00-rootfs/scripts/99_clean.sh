#!/bin/bash

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"
ROOTFS_DIR="$(realpath "$1")"
ORG_ROOTFS_DIR="${ROOTFS_DIR}.org"

set -e

rm -rf "$ROOTFS_DIR/var/cache/apt/"
rm -rf "$ROOTFS_DIR/var/lib/apt/lists/"
rm -rf "$ROOTFS_DIR/tmp/"*
rm -rf "$ROOTFS_DIR/usr/share/locale/"
rm -rf "$ROOTFS_DIR/etc/machine-id"
