#!/usr/bin/env bash

if [[ -z "$CREATE_FIRMWARE" ]]; then
  echo "Error: This script should be run within the create_firmware.sh environment."
  exit 1
fi

set -e

TARGET_DIR="$CACHE_DIR/repos/prometheus-klipper-exporter"
cache_git.sh prometheus-klipper-exporter "$TARGET_DIR"

echo ">> Compiling prometheus-klipper-exporter..."
# Note: Requires Go toolchain in build environment
GOOS=linux GOARCH=arm64 CGO_ENABLED=0 go -C "$TARGET_DIR" build -o "$1/usr/local/bin/prometheus-klipper-exporter" .

echo ">> Validate binaries..."
stat "$1/usr/local/bin/prometheus-klipper-exporter" >/dev/null
