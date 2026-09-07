#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-PackageHomePage: https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware
# SPDX-FileCopyrightText: Copyright (c) 2026 @paxx12

if [[ -z "$CREATE_FIRMWARE" ]]; then
  echo "Error: This script should be run within the create_firmware.sh environment."
  exit 1
fi

set -eo pipefail

echo ">> Checking for fluidd nginx configurations..."
if [[ ! -f "$ROOTFS_DIR/etc/nginx/sites-available/fluidd" ]]; then
  echo "ERROR: fluidd not found at $ROOTFS_DIR/etc/nginx/sites-available/fluidd"
  exit 1
fi
if [[ ! -L "$ROOTFS_DIR/etc/nginx/sites-enabled/fluidd" ]]; then
  echo "ERROR: fluidd not found at $ROOTFS_DIR/etc/nginx/sites-enabled/fluidd"
  exit 1
fi

VERSION=v2.19.0
URL=https://github.com/mainsail-crew/mainsail/releases/download/$VERSION/mainsail.zip
SHA256=c4d9d96f89851c6ae0709c2f20725447f3fe8c57cf193869b0083441bd93378a
FILENAME=mainsail-$VERSION.zip

rm -rf "$ROOTFS_DIR/home/lava/mainsail"

cache_file.sh "$CACHE_DIR/$FILENAME" "$URL" "$SHA256" "$ROOTFS_DIR/home/lava/mainsail"
