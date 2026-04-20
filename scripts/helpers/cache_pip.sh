#!/usr/bin/env bash

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <rootfs-dir> [pip params]"
  exit 1
fi

ROOTFS_DIR="$1"
shift

pip3_cmd() {
  chroot_firmware.sh "$ROOTFS_DIR" /usr/bin/pip3 "$@"
}

if [[ -n "$CI" ]]; then
  # In CI always prefer network dependencies
  pip3_cmd install "$@"
elif ! pip3_cmd install --no-index --find-links=/root/pip "$@"; then
  # Unless CI prefer cached dependencies
  pip3_cmd download -d /root/pip "$@"
  pip3_cmd install --no-index --find-links=/root/pip "$@"
fi
