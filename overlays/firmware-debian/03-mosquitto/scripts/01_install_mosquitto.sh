#!/bin/bash

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"
ROOTFS_DIR="$(realpath "$1")"

set -e

in_chroot() {
  "$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$ROOTFS_DIR" bash -c "$@"
}

echo ">> Installing mosquitto MQTT broker..."
in_chroot 'apt update && apt install -y mosquitto mosquitto-clients'

echo ">> Enabling mosquitto service..."
in_chroot 'systemctl enable mosquitto'

echo ">> Mosquitto installation complete"
