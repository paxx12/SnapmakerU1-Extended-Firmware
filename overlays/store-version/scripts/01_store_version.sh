#!/bin/bash

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

ROOTFS_DIR="$(realpath "$1")"

if [[ -n "$GIT_VERSION" ]]; then
  ABBRV=$(git describe --abbrev --always)

  # 0.9.0-paxx12-1-gabcdef0
  echo "${GIT_VERSION#v}" > "$ROOTFS_DIR/etc/VERSION"
  echo "${GIT_VERSION#v}_$(date +%Y%m%d%H%M%S)_${ABBRV}" > "$ROOTFS_DIR/etc/CUSTOMVERSION"
fi
