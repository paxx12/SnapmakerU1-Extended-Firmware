#!/bin/bash

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"

GIT_URL=https://github.com/paxx12/v4l2-mpp.git
GIT_SHA=468fe35b159977a6e86f75f5e9024cb404eaa71d

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

echo ">> Setting up cross-compilation environment..."
export CROSS_COMPILE=aarch64-linux-gnu-
export CC="${CROSS_COMPILE}gcc"
export CXX="${CROSS_COMPILE}g++"
export AR="${CROSS_COMPILE}ar"
export RANLIB="${CROSS_COMPILE}ranlib"
export STRIP="${CROSS_COMPILE}strip"

echo ">> Compiling dependencies..."
make -C "$TARGET_DIR" deps

echo ">> Compiling v4l2-mpp applications..."
make -C "$TARGET_DIR" install DESTDIR="$1"

echo ">> Validate binaries..."
stat "$1/usr/local/bin/capture-v4l2-jpeg-mpp" >/dev/null
stat "$1/usr/local/bin/capture-v4l2-raw-mpp" >/dev/null
stat "$1/usr/local/bin/stream-rtsp" >/dev/null
stat "$1/usr/local/bin/stream-webrtc" >/dev/null
stat "$1/usr/local/bin/stream-http.py" >/dev/null
stat "$1/usr/local/bin/control-v4l2.py" >/dev/null
echo ">> v4l2-mpp installation completed successfully."
