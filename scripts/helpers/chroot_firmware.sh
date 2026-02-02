#!/usr/bin/env bash

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <rootfs> <cmd> [args...]"
  exit 1
fi

ROOTFS="$(realpath "$1")"
shift

cd "$ROOTFS"

if [[ -e ./etc/resolv.conf ]]; then
  echo "[!] The ./etc/resolv.conf file already exists. Failing."
  exit 1
fi

set -euo pipefail

echo "nameserver 1.1.1.1" > ./etc/resolv.conf
trap 'rm -f ./etc/resolv.conf' EXIT

chroot "$ROOTFS" "$@"
