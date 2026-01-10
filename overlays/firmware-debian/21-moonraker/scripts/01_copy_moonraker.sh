#!/bin/bash

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"
ROOTFS_DIR="$(realpath "$1")"
ORG_ROOTFS_DIR="${ROOTFS_DIR}.org"

set -e

mkdir_chroot() {
  for dir; do
    echo ">> Creating directory $dir in chroot..."
    mkdir -p "$ROOTFS_DIR/$dir"
  done
}

copy_chroot() {
  local target="$1"
  shift

  echo ">> Copying to $target the $@..."
  for src; do
    cp -rv -L --remove-destination "$ORG_ROOTFS_DIR/$src" "$ROOTFS_DIR/$target"
  done
}

in_chroot() {
  "$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$ROOTFS_DIR" bash -c "$@"
}

echo ">> Copying Moonraker from /home/lava/moonraker to /opt/moonraker..."
mkdir_chroot /opt/moonraker
copy_chroot /opt/moonraker/ /home/lava/moonraker/.

echo ">> Creating virtual environment in /opt/moonraker..."
in_chroot 'python3 -m venv /opt/moonraker/venv'

echo ">> Installing moonraker requirements..."
in_chroot '/opt/moonraker/venv/bin/pip3 install --upgrade pip'
in_chroot '/opt/moonraker/venv/bin/pip3 install -r /opt/moonraker/scripts/moonraker-requirements.txt'

echo ">> Setting ownership to lava:lava..."
in_chroot 'chown -R lava:lava /opt/moonraker'

echo ">> Moonraker installation complete"
