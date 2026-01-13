#!/bin/bash

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"

GIT_URL=https://github.com/horzadome/snapmaker-u1-timelapse-recovery.git
GIT_SHA=8e2a2e50e8642a4f368e4e4794585b2a2d2e2857

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

set -eo pipefail

TARGET_DIR="$ROOT_DIR/tmp/snapmaker-u1-timelapse-recovery"

if [[ ! -d "$TARGET_DIR" ]]; then
  git clone "$GIT_URL" "$TARGET_DIR" --recursive
  if ! git -C "$TARGET_DIR" checkout "$GIT_SHA"; then
    git fetch origin "$GIT_SHA"
    git -C "$TARGET_DIR" checkout "$GIT_SHA"
  fi
fi

echo ">> Installing Timelapse Recovery Tool..."
if [ ! -d "$1/usr/local/bin" ]; then
  mkdir -p "$1/usr/local/bin"
fi

if ! cp "$TARGET_DIR/fix_timelapse.py" "$1/usr/local/bin/fix_timelapse"; then
  echo ">> ERROR: Failed to copy fix_timelapse.py to target rootfs."
  exit 1
fi
chmod +x "$1/usr/local/bin/fix_timelapse"
echo ">> Validate binaries..."
stat "$1/usr/local/bin/fix_timelapse" >/dev/null

echo ">> Timelapse Recovery Tool installation complete."
