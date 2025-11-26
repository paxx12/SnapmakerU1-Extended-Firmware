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
  git -C "$TARGET_DIR" checkout b28cf38c484e281e0b234a06aac2a7a9e524d710
fi

echo ">> Compiling MPP library..."
"$TARGET_DIR/deps/compile_mpp.sh"

echo ">> Compiling libdatachannel library..."
"$TARGET_DIR/deps/compile_libdatachannel.sh"

echo ">> Compiling v4l2-mpp applications..."
make -C "$TARGET_DIR" install DESTDIR="$1"
