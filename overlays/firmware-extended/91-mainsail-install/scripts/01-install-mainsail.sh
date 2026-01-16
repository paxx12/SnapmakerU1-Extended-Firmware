#!/bin/bash

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

set -eo pipefail

ROOTFS_DIR="$1"
TARGET_DIR="$ROOT_DIR/tmp"

echo ">> Checking for fluidd nginx configurations..."
if [[ ! -f "$ROOTFS_DIR/etc/nginx/sites-available/fluidd" ]]; then
  echo "ERROR: fluidd not found at $ROOTFS_DIR/etc/nginx/sites-available/fluidd"
  exit 1
fi
if [[ ! -L "$ROOTFS_DIR/etc/nginx/sites-enabled/fluidd" ]]; then
  echo "ERROR: fluidd not found at $ROOTFS_DIR/etc/nginx/sites-enabled/fluidd"
  exit 1
fi

VERSION=v2.17.0
URL=https://github.com/mainsail-crew/mainsail/releases/download/$VERSION/mainsail.zip
SHA256=d010f4df25557d520ccdbb8e42fc381df2288e6a5c72d3838a5a2433c7a31d4e
FILENAME=mainsail-$VERSION.zip

if [[ ! -f "$TARGET_DIR/$FILENAME" ]]; then
  echo ">> Downloading $FILENAME..."
  wget -O "$TARGET_DIR/$FILENAME" "$URL"
fi

echo ">> Verifying $FILENAME checksum..."
echo "$SHA256  $TARGET_DIR/$FILENAME" | sha256sum --check --status

echo ">> Extracting $FILENAME..."
rm -rf "$TARGET_DIR/mainsail-$VERSION"
unzip -o "$TARGET_DIR/$FILENAME" -d "$TARGET_DIR/mainsail-$VERSION"

echo ">> Installing $FILENAME to target rootfs..."
rm -rf "$1/home/lava/mainsail"
cp -r "$TARGET_DIR/mainsail-$VERSION" "$1/home/lava/mainsail"
