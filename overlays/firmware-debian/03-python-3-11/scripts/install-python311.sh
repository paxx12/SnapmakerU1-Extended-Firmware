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

echo ">> Uninstalling all current Python packages..."
in_chroot 'apt-get remove -y python3* libpython3*'
in_chroot 'apt-get autoremove -y'

echo ">> Adding bookworm repository to apt sources..."
in_chroot 'echo "deb http://deb.debian.org/debian bookworm main" > /etc/apt/sources.list.d/bookworm.list'
in_chroot 'apt-get update'

echo ">> Installing Python 3.11 and development headers from bookworm..."
in_chroot 'apt-get install -t bookworm -y python3-dev python3.11-venv'
in_chroot 'python3.11 --version'

# echo ">> Removing bookworm repository from apt sources..."
# in_chroot 'rm -f /etc/apt/sources.list.d/bookworm.list'
# in_chroot 'apt-get update'
