#!/bin/bash

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

set -eo pipefail

TARGET_DIR="$ROOT_DIR/tmp"

VERSION=v1.35.1
URL=https://github.com/fluidd-core/fluidd/releases/download/$VERSION/fluidd.zip
SHA256=5b8b525d9c65b2dfa83b238ee8fded105d1b34e3b73862aed10411bf977bb8f0
FILENAME=fluidd-$VERSION.zip

if [[ ! -f "$TARGET_DIR/$FILENAME" ]]; then
  echo ">> Downloading $FILENAME..."
  wget -O "$TARGET_DIR/$FILENAME" "$URL"
fi

echo ">> Verifying $FILENAME checksum..."
echo "$SHA256  $TARGET_DIR/$FILENAME" | sha256sum --check --status

echo ">> Extracting $FILENAME..."
rm -rf "$TARGET_DIR/fluidd-$VERSION"
unzip -o "$TARGET_DIR/$FILENAME" -d "$TARGET_DIR/fluidd-$VERSION"

echo ">> Installing $FILENAME to target rootfs..."
rm -rf "$1/home/lava/fluidd"
cp -r "$TARGET_DIR/fluidd-$VERSION" "$1/home/lava/fluidd"
