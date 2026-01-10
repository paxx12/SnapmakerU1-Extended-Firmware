#!/bin/bash

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"
ROOTFS_DIR="$(realpath "$1")"
TMP_DIR="$ROOT_DIR/tmp"
MOONRAKER_REPO="https://github.com/Arksine/moonraker.git"
MOONRAKER_SHA="b3f9566b8b8863ec85a00ce424d77c8e19576c44"

set -e

in_chroot() {
  "$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$ROOTFS_DIR" bash -c "$@"
}

mkdir_chroot() {
  for dir; do
    echo ">> Creating directory $dir in chroot..."
    mkdir -p "$ROOTFS_DIR/$dir"
  done
}

TARGET_DIR="$TMP_DIR/moonraker"

echo ">> Cloning moonraker from $MOONRAKER_REPO..."
if [[ ! -d "$TARGET_DIR" ]]; then
  git clone "$MOONRAKER_REPO" "$TARGET_DIR" --recursive
  if ! git -C "$TARGET_DIR" checkout "$MOONRAKER_SHA"; then
    git fetch origin "$MOONRAKER_SHA"
    git -C "$TARGET_DIR" checkout "$MOONRAKER_SHA"
  fi
fi

echo ">> Copying moonraker files to rootfs..."
mkdir_chroot /opt/moonraker
cp -rv "$TMP_DIR/moonraker"/* "$ROOTFS_DIR/opt/moonraker/"

echo ">> Installing Python3 and venv in chroot..."
in_chroot 'apt update && apt install -y python3 python3-venv python3-dev python3-pip build-essential libopenjp2-7 python3-libgpiod curl libcurl4-openssl-dev libssl-dev liblmdb-dev libsodium-dev zlib1g-dev libjpeg-dev packagekit git'

echo ">> Creating virtual environment in /opt/moonraker..."
in_chroot 'python3 -m venv /opt/moonraker/venv'

echo ">> Installing moonraker requirements..."
in_chroot '/opt/moonraker/venv/bin/pip3 install --upgrade pip'
in_chroot '/opt/moonraker/venv/bin/pip3 install -r /opt/moonraker/scripts/moonraker-requirements.txt'

echo ">> Setting ownership to lava:lava..."
in_chroot 'chown -R lava:lava /opt/moonraker'

echo ">> Moonraker installation complete"
