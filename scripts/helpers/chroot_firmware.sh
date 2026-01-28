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
ROOT_CACHE="$CACHE_DIR/root-cache"
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
  umount -l ./root/.cache
  umount -l ./firmware-root
  rmdir ./firmware-root
}

trap cleanup EXIT

mkdir -p "$ROOT_CACHE" ./root/.cache
mkdir -p ./firmware-root

mount --bind "$ROOT_CACHE" ./root/.cache
mount -t proc /proc ./proc
mount --bind /sys ./sys
mount --bind /dev ./dev
mount --bind "$ROOT_DIR" ./firmware-root

chroot "$ROOTFS" "$@"
