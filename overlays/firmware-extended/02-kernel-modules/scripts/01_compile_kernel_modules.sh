#!/usr/bin/env bash

if [[ -z "$CREATE_FIRMWARE" ]]; then
  echo "Error: This script should be run within the create_firmware.sh environment."
  exit 1
fi

KERNEL_CONFIG="$ROOTFS_DIR/info/config-6.1"
KERNEL_SRC_DIR="$CACHE_DIR/repos/kernel"
KERNEL_BUILD_DIR="$BUILD_DIR/kernel"
OUT_DIR="$ROOTFS_DIR/lib/modules"

set -xeo pipefail

cache_git.sh kernel "$KERNEL_SRC_DIR"

rm -rf "$KERNEL_BUILD_DIR"
mkdir -p "$KERNEL_BUILD_DIR"
cp -v "$KERNEL_CONFIG" "$KERNEL_BUILD_DIR/.config"

kernel_make() {
  make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- O="$KERNEL_BUILD_DIR" "$@"
}

module_make() {
  local dir="$1"
  shift 1
  make -C "$dir" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- O="$KERNEL_BUILD_DIR" "$@"
}

kernel_module_make() {
  make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- O="$KERNEL_BUILD_DIR" "$@" modules
}

pushd "$KERNEL_SRC_DIR"

scripts/config --file "$KERNEL_BUILD_DIR/.config" \
  --module CONFIG_TUN
:| kernel_make olddefconfig
kernel_make modules_prepare

# Individual modules
kernel_make drivers/net/tun.ko

mkdir -p "$OUT_DIR"
# do not overwrite existing modules
find "$KERNEL_BUILD_DIR" -type f -name '*.ko' -exec cp -vn '{}' "$OUT_DIR/" ';'
