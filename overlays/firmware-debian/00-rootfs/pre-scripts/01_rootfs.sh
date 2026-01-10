#!/bin/bash

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"
ROOTFS_DIR="$(realpath "$1")"
TMP_DIR="$ROOT_DIR/tmp"

VERSION=20260110-941b6cc
FILENAME="debian-rootfs-trixie-$VERSION.tgz"
TMP_FILENAME="$ROOT_DIR/tmp/$FILENAME"
URL="https://github.com/Snapmaker-U1-Extended-Firmware/base-debian-os/releases/download/$VERSION/$FILENAME"
SHA256="f0bf9db49e70d8100e1714b9679c6c1d1d61f5fe897d1b6f1acc333ed6766240"

set -e

echo ">> Downloading debian rootfs tarball..."
"$ROOT_DIR/scripts/helpers/download_file.sh" "$TMP_FILENAME" "$URL" "$SHA256"


if [[ ! -d "${ROOTFS_DIR}.org" ]]; then
  echo ">> Backuping rootfs..."
  mv "$ROOTFS_DIR"{,.org}
else
  echo ">> Cleaning rootfs..."
  rm -rf "$ROOTFS_DIR"
fi

echo ">> Extracting rootfs..."
mkdir -p "$ROOTFS_DIR"
tar -xzf "$TMP_FILENAME" -C "$ROOTFS_DIR"

# EXTRA_DEPS="iw net-tools wireless-tools"

# if [[ $(cat "$ROOTFS_DIR/.deps" || true) != "$EXTRA_DEPS" ]]; then
#   "$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$ROOTFS_DIR" bash -c "apt update -y && apt install -y $EXTRA_DEPS"
#   echo "$EXTRA_DEPS" > "$ROOTFS_DIR/.deps"
# fi

echo ">> Debian Bootstrap installed to $ROOTFS_DIR"
