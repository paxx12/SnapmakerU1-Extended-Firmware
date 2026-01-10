#!/bin/bash

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"
ROOTFS_DIR="$(realpath "$1")"

set -e

echo ">> Creating required directories..."
mkdir -p "$ROOTFS_DIR/"{overlay,rom,oem,userdata}

echo ">> Enabling multi-user.target as default..."
"$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$ROOTFS_DIR" systemctl set-default multi-user.target

echo ">> Disabling systemd-networkd-wait-online.service..."
"$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$ROOTFS_DIR" bash -c "systemctl disable systemd-networkd-wait-online.service"

echo ">> Installing systemd-resolved..."
"$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$ROOTFS_DIR" systemctl enable systemd-resolved
ln -sf /run/systemd/resolve/stub-resolv.conf "$ROOTFS_DIR/etc/resolv.conf"
