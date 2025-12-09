#!/bin/bash

ROOT_DIR="$(realpath "$(dirname "$0")/../../..")"

GIT_URL=https://github.com/paxx12/v4l2-mpp.git
GIT_SHA=7fd769a0a37d9592bee809b60d2e774eb49305d8

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

set -eo pipefail

TARGET_DIR="$ROOT_DIR/tmp/v4l2-mpp"

if [[ ! -d "$TARGET_DIR" ]]; then
  git clone "$GIT_URL" "$TARGET_DIR" --recursive
  if ! git -C "$TARGET_DIR" checkout "$GIT_SHA"; then
    git fetch origin "$GIT_SHA"
    git -C "$TARGET_DIR" checkout "$GIT_SHA"
  fi
fi

echo ">> Compiling dependencies..."
make -C "$TARGET_DIR" deps

echo ">> Compiling v4l2-mpp applications..."
make -C "$TARGET_DIR" install DESTDIR="$1"
