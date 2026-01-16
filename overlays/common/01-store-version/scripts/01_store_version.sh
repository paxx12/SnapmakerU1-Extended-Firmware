#!/bin/bash

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

ROOTFS_DIR="$(realpath "$1")"

ABBRV=$(git describe --abbrev --always)

if [[ -n "$GIT_VERSION" ]]; then
  # 0.9.0-paxx12-1-gabcdef0
  echo "${GIT_VERSION#v}-${ABBRV}" > "$ROOTFS_DIR/etc/BUILD_VERSION"
else
  # <git-branch-name>-<abbr>
  GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
  echo "${GIT_BRANCH}-${ABBRV}" > "$ROOTFS_DIR/etc/BUILD_VERSION"
fi

if [[ -n "$PROFILE" ]]; then
  echo "$PROFILE" > "$ROOTFS_DIR/etc/BUILD_PROFILE"
fi
