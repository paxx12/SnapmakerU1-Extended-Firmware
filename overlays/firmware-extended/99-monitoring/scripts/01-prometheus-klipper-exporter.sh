#!/bin/bash

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"

GIT_URL=https://github.com/scross01/prometheus-klipper-exporter.git
GIT_SHA=9eacec280108a4da8156b47c01c2862219d86ecd

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

set -eo pipefail

TARGET_DIR="$ROOT_DIR/tmp/prometheus-klipper-exporter"

if [[ ! -d "$TARGET_DIR" ]]; then
  git clone "$GIT_URL" "$TARGET_DIR" --recursive
  if ! git -C "$TARGET_DIR" checkout "$GIT_SHA"; then
    git fetch origin "$GIT_SHA"
    git -C "$TARGET_DIR" checkout "$GIT_SHA"
  fi
fi

echo ">> Compiling prometheus-klipper-exporter..."
# Note: Requires Go toolchain in build environment
GOOS=linux GOARCH=arm64 CGO_ENABLED=0 go -C "$TARGET_DIR" build -o "$1/usr/local/bin/prometheus-klipper-exporter" .

echo ">> Validate binaries..."
file "$1/usr/local/bin/prometheus-klipper-exporter"

echo ">> Prometheus Klipper Exporter installation complete."
