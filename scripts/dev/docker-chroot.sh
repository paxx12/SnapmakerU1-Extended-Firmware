#!/usr/bin/env bash
set -e

if [ $# -lt 1 ]; then
  echo "Usage: $0 <rootfs> [args...]"
  exit 1
fi

ROOTFS="$(realpath "$1")"
shift

if [[ $# -eq 0 ]]; then
  set -- bash -i
fi

exec docker run --rm -it \
  -v "$ROOTFS:/rootfs" \
  -v /dev:/rootfs/dev:ro \
  -v /proc:/rootfs/proc:ro \
  -v /sys:/rootfs/sys:ro \
  -v /etc/resolv.conf:/rootfs/etc/resolv.conf:ro \
  alpine chroot /rootfs "$@"
