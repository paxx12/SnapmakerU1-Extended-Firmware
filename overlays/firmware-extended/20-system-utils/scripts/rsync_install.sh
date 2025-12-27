#!/bin/bash

set -eo pipefail

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

echo ">> Installing rsync from precompiled tarball"

TARGET_DIR="$ROOT_DIR/tmp"

VERSION=3.2.7
FILENAME=rsync-$VERSION.tar.gz
URL=https://download.samba.org/pub/rsync/binaries/centos-8-aarch64/$FILENAME
BIN_SHA256=e4a9044b9cc6e3a11f89dbe3b728e54870d53726a718fd0c50fce460da36d2db

if [[ ! -f "$TARGET_DIR/$FILENAME" ]]; then
  echo ">> Downloading $FILENAME..."
  wget -O "$TARGET_DIR/$FILENAME" "$URL"
fi

echo ">> Extracting $FILENAME..."
mkdir -p "$1/usr/local/bin"
if ! tar -xzf "$TARGET_DIR/$FILENAME" -C "$1" usr/local/bin/rsync; then
  echo "[!] Failed to extract rsync from $FILENAME"
  exit 1
fi

echo ">> Verifying /usr/local/bin/rsync checksum..."
echo "$BIN_SHA256  $1/usr/local/bin/rsync" | sha256sum --check --status

echo ">> Verifying if rsync is executable..."
if [[ ! -x "$1/usr/local/bin/rsync" ]]; then
  echo "[!] /usr/local/bin/rsync is not executable."
  exit 1
fi

echo ">> rsync installed to $1/usr/local/bin"
