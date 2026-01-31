#!/bin/bash

if [[ -z "$CREATE_FIRMWARE" ]]; then
  echo "Error: This script should be run within the create_firmware.sh environment."
  exit 1
fi

KERNEL_CONFIG="$ROOTFS_DIR/info/config-6.1"
KERNEL_SRC_DIR="$ROOT_DIR/tmp/kernel"
KERNEL_BUILD_DIR="$BUILD_DIR/kernel"
OUT_DIR="$ROOTFS_DIR/lib/modules"

set -xeo pipefail

source "$ROOT_DIR/vars.mk"

if [[ ! -d "$KERNEL_SRC_DIR/.git" ]]; then
  git init "$KERNEL_SRC_DIR"
fi

pushd "$KERNEL_SRC_DIR"

if ! git checkout -f "$KERNEL_SHA"; then
  git remote set-url origin "$KERNEL_GIT_URL" || git remote add origin "$KERNEL_GIT_URL"
  git fetch --progress origin "$KERNEL_SHA" --depth=1
  git checkout "$KERNEL_SHA"
fi

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

scripts/config --file "$KERNEL_BUILD_DIR/.config" \
  --module CONFIG_TUN
:| kernel_make olddefconfig
kernel_make modules_prepare

# Individual modules
kernel_make drivers/net/tun.ko

mkdir -p "$OUT_DIR"
# do not overwrite existing modules
find "$KERNEL_BUILD_DIR" -type f -name '*.ko' -exec cp -vn '{}' "$OUT_DIR/" ';'
