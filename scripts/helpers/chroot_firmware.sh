#!/usr/bin/env bash

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <rootfs> <cmd> [args...]"
  exit 1
fi

if [[ -z "$CREATE_FIRMWARE" ]]; then
  echo "Error: This script should be run within the create_firmware.sh environment."
  exit 1
fi

ROOTFS="$(realpath "$1")"
shift

cd "$ROOTFS"

cleanup() {
  mountpoint "$ROOTFS/root" && umount "$ROOTFS/root"
  rm -rf "$ROOTFS/root"
  mkdir -p "$ROOTFS/root"

  [[ -e ./etc/resolv.conf.bak ]] && mv ./etc/resolv.conf.bak ./etc/resolv.conf
  rm -f ./etc/resolv.conf
}

if [[ -e ./etc/resolv.conf ]]; then
  mv ./etc/resolv.conf ./etc/resolv.conf.bak
fi

trap 'cleanup' EXIT

if [[ -z "$CI" ]]; then
  # Cache /root
  mkdir -p "$CHROOT_CACHE/root"
  mount --bind "$CHROOT_CACHE/root" "$ROOTFS/root"
fi

set -euo pipefail

echo "nameserver 1.1.1.1" > ./etc/resolv.conf
chroot "$ROOTFS" "$@"
