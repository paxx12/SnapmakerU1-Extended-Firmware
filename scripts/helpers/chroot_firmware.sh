#!/usr/bin/env bash

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <rootfs> <cmd> [args...]"
  exit 1
fi

ROOTFS="$(realpath "$1")"
ROOT_DIR="$(dirname "$ROOTFS")/../.."
CACHE_DIR="$ROOT_DIR/tmp/root-cache"
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

mkdir -p "$CACHE_DIR" ./root/.cache
mkdir -p ./firmware-root

mount --bind "$CACHE_DIR" ./root/.cache
mount -t proc /proc ./proc
mount --bind /sys ./sys
mount --bind /dev ./dev
mount --bind "$ROOT_DIR" ./firmware-root

chroot "$ROOTFS" "$@"
