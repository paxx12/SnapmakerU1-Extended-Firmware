#!/bin/bash

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"
ROOTFS_DIR="$(realpath "$1")"
TMP_DIR="$ROOT_DIR/tmp"

FILENAME="debian-rootfs-trixie-20260110-2011b81.tgz"
TMP_FILENAME="$ROOT_DIR/tmp/$FILENAME"
URL="https://github.com/Snapmaker-U1-Extended-Firmware/base-debian-os/releases/download/20260110-2011b81/debian-rootfs-trixie-20260110-2011b81.tgz" \
SHA256="710b68c646ef46c9c6f82ff38835421df3f5f497cc5723cc4373ed15a29d7c1f"

set -e

echo ">> Downloading debian rootfs tarball..."
"$ROOT_DIR/scripts/helpers/download_file.sh" "$TMP_FILENAME" "$URL" "$SHA256"

# EXTRA_DEPS="libcurl4 wpasupplicant udev"

# if [[ $(cat "$DEBOOTSTRAP_DIR/.deps" || true) != "$EXTRA_DEPS" ]]; then
#   "$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$DEBOOTSTRAP_DIR" apt install -y $EXTRA_DEPS
#   echo "$EXTRA_DEPS" > "$DEBOOTSTRAP_DIR/.deps"
# fi

if [[ ! -d "${ROOTFS_DIR}.org" ]]; then
  echo ">> Backuping rootfs..."
  mv "$ROOTFS_DIR"{,.org}
else
  echo ">> Cleaning rootfs..."
  rm -rf "$ROOTFS_DIR"
fi

echo ">> Extracting rootfs..."
mkdir -p "$ROOTFS_DIR"
tar -xzf "$TMP_DIR/debian-rootfs-trixie-20260110-2011b81.tgz" -C "$ROOTFS_DIR"

echo ">> Debian Bootstrap installed to $ROOTFS_DIR"
