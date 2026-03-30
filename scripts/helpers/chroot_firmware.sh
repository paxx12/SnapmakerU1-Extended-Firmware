#!/usr/bin/env bash

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <rootfs> <cmd> [args...]"
  exit 1
fi

ROOTFS="$(realpath "$1")"
shift

cd "$ROOTFS"

if [[ -e ./etc/resolv.conf ]]; then
  mv ./etc/resolv.conf ./etc/resolv.conf.bak
  trap 'mv ./etc/resolv.conf.bak ./etc/resolv.conf' EXIT
else
  trap 'rm -f ./etc/resolv.conf' EXIT
fi

set -euo pipefail

echo "nameserver 1.1.1.1" > ./etc/resolv.conf
chroot "$ROOTFS" "$@"
