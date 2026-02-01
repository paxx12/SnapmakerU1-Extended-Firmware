#!/usr/bin/env bash

if [[ -z "$CREATE_FIRMWARE" ]]; then
  echo "Error: This script should be run within the create_firmware.sh environment."
  exit 1
fi

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <rootfs> <cmd> [args...]"
  exit 1
fi

ROOTFS="$(realpath "$1")"
shift

cd "$ROOTFS"

[[ -e ./etc/resolv.conf ]] && mv ./etc/resolv.conf{,.bak}
echo "nameserver 1.1.1.1" > ./etc/resolv.conf

cleanup() {
  rm -f ./etc/resolv.conf
  [[ -e ./etc/resolv.conf.bak ]] && mv ./etc/resolv.conf{.bak,}
  umount -l ./proc
  umount -l ./sys
  umount -l ./dev
  umount -l ./tmp
}

trap cleanup EXIT

set -e

mount -t proc /proc ./proc
mount --bind /sys ./sys
mount --bind /dev ./dev
mount --bind "$ROOT/tmp" ./tmp

# configure chroot caches
export PIP_CACHE_DIR="/tmp/cache-pip"
export GOPATH="/tmp/cache-go"

chroot "$ROOTFS" "$@"
