#!/bin/bash

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

set -eo pipefail

TARGET_DIR="$ROOT_DIR/tmp"

VERSION=v1.7.0-beta
URL=https://github.com/novnc/noVNC/archive/refs/tags/$VERSION.tar.gz
SHA256=25568d7203ade087387695bf80790ff2c53644fa8bbf5e3b7c917e16d828e475
FILENAME=novnc-$VERSION.tar.gz

if [[ ! -f "$TARGET_DIR/$FILENAME" ]]; then
  echo ">> Downloading $FILENAME..."
  wget -O "$TARGET_DIR/$FILENAME" "$URL"
fi

echo ">> Verifying $FILENAME checksum..."
echo "$SHA256  $TARGET_DIR/$FILENAME" | sha256sum --check --status

echo ">> Extracting $FILENAME..."
rm -rf "$TARGET_DIR/noVNC-${VERSION#v}"
tar -xzf "$TARGET_DIR/$FILENAME" -C "$TARGET_DIR"

echo ">> Installing noVNC to target rootfs..."
rm -rf "$1/home/lava/novnc"
cp -r "$TARGET_DIR/noVNC-${VERSION#v}" "$1/home/lava/novnc"
cp "$(dirname "$0")/../novnc-defaults.json" "$1/home/lava/novnc/defaults.json"
cp "$(dirname "$0")/../novnc-mandatory.json" "$1/home/lava/novnc/mandatory.json"

echo ">> noVNC installed to /home/lava/novnc"
