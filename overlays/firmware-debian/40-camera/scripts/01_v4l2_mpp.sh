#!/bin/bash

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"

GIT_URL=https://github.com/paxx12/v4l2-mpp.git
GIT_SHA=eed72ef7f772072aaff50c71dbf3f67c364414ff

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
file "$1/usr/local/bin/capture-v4l2-jpeg-mpp"
file "$1/usr/local/bin/capture-v4l2-raw-mpp"
file "$1/usr/local/bin/fake-service"
file "$1/usr/local/bin/stream-rtsp"
file "$1/usr/local/bin/stream-webrtc"
file "$1/usr/local/bin/stream-snap-mqtt.py"
file "$1/usr/local/bin/stream-http.py"

echo ">> Creating timelapse directory..."
mkdir -p "$1/userdata/.tmp_timelapse"

echo ">> Installing Python dependencies..."
"$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$1" /opt/venv/bin/pip3 install paho-mqtt

echo ">> v4l2-mpp installation completed successfully."
