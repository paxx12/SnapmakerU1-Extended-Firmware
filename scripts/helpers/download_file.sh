#!/usr/bin/env bash

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 <target-file> <url> <sha256>"
  exit 1
fi

TARGET="$1"
URL="$2"
SHA256="$3"

TARGET_DIR="$(dirname "$TARGET")"
FILENAME="$(basename "$TARGET")"

set -e
mkdir -p "$TARGET_DIR"

if [[ ! -f "$TARGET" ]]; then
  echo ">> Downloading $FILENAME..."
  wget -O "$TARGET" "$URL"
fi

echo ">> Verifying $TARGET checksum..."
if ! echo "$SHA256  $TARGET" | sha256sum --check --status; then
  echo "[!] SHA256 checksum mismatch for $FILENAME"
  exit 1
fi
