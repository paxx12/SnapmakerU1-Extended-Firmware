#!/bin/bash

ROOT_DIR="$(realpath "$(dirname "$0")/../../..")"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

set -eo pipefail

TARGET_DIR="$ROOT_DIR/tmp/v4l2-mpp"

if [[ ! -d "$TARGET_DIR" ]]; then
  git clone https://github.com/paxx12/v4l2-mpp.git "$TARGET_DIR" --recursive
  git -C "$TARGET_DIR" checkout 3ab6a4b1933496f52ff883301de1b34371881538
fi

echo ">> Compiling MPP library..."
"$TARGET_DIR/deps/compile_mpp.sh"

echo ">> Compiling v4l2-mpp applications..."
make -C "$TARGET_DIR" install DESTDIR="$1"
