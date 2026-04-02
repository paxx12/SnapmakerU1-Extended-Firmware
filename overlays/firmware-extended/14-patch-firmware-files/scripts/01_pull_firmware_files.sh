#!/usr/bin/env bash

if [[ -z "$CREATE_FIRMWARE" ]]; then
  echo "Error: This script should be run within the create_firmware.sh environment."
  exit 1
fi

set -eo pipefail

FIRMWARE_FILES=(
  # RTL8153A (USB 3.0, revision A)
  rtl_nic/rtl8153a-4.fw
  # RTL8153B (USB 3.0, revision B)
  rtl_nic/rtl8153b-2.fw
  # RTL8153C (USB 3.0, revision C)
  rtl_nic/rtl8153c-1.fw
  # RTL8156A (USB 3.0, 2.5G, revision A)
  rtl_nic/rtl8156a-2.fw
  # RTL8156B (USB 3.0, 2.5G, revision B)
  rtl_nic/rtl8156b-2.fw
)

HOST_FIRMWARE_DIR=/usr/lib/firmware
ROOTFS_FIRMWARE_DIR="$ROOTFS_DIR/lib/firmware"

for fw_file in "${FIRMWARE_FILES[@]}"; do
  dest="$ROOTFS_FIRMWARE_DIR/$fw_file"
  src="$HOST_FIRMWARE_DIR/$fw_file"

  if [[ -e "$dest" ]]; then
    echo "Error: '$fw_file' already exists in firmware rootfs — refusing to overwrite."
    exit 1
  fi

  if [[ ! -f "$src" ]]; then
    echo "Error: '$fw_file' not found on host system at '$src'."
    exit 1
  fi

  echo "[+] Pulling firmware: $fw_file"
  install -D -m 644 "$src" "$dest"
done
