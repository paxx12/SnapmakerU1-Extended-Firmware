#!/bin/bash

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"
ROOTFS_DIR="$(realpath "$1")"
ORG_ROOTFS_DIR="${ROOTFS_DIR}.org"

set -e

copy_bin() {
  local src="$1"
  local target="$2"
  shift 2

  echo ">> Copying $src to $target ..."
  mkdir -p "$ROOTFS_DIR/$target"
  cp -rv -L --remove-destination "$ORG_ROOTFS_DIR/$src" "$ROOTFS_DIR/$target"

  if [[ $# -gt 0 ]]; then
    echo ">> Testing $@..."
    if ! "$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$ROOTFS_DIR" "$@"; then
      echo ">> ERROR: Testing $@ failed after copying $src to $target"
      exit 1
    fi
  fi
}

in_chroot() {
  "$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$ROOTFS_DIR" bash -c "$@"
}

test_bin() {
  if ! "$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$ROOTFS_DIR" bash -c "$@"; then
    echo ">> ERROR: Testing $@ failed after copying $src to $target"
    exit 1
  fi
}

# validate ldd that there are no missing files
validate_ldd() {
  local bin_path="$1"
  echo ">> Validating ldd for $bin_path ..."
  missing_libs=$("$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$ROOTFS_DIR" bash -c "LD_LIBRARY_PATH=/opt/lava/lib ldd $bin_path" | grep "not found" || true)
  if [[ -n "$missing_libs" ]]; then
    echo ">> ERROR: Missing libraries for $bin_path:"
    echo "$missing_libs"
    exit 1
  fi
}

mkdir_chroot() {
  local dir="$1"
  echo ">> Creating directory $dir in chroot..."
  mkdir -p "$ROOTFS_DIR/$dir"
}

# copy all lib
mkdir_chroot /opt/lava/lib
copy_bin /usr/lib/librkwifibt.so /opt/lava/lib/
copy_bin /usr/lib/libzlog.so.1.2 /opt/lava/lib/
copy_bin /usr/lib/libjpeg.so.8 /opt/lava/lib/
copy_bin /usr/lib/libwpa_client.so /opt/lava/lib/

# updateEngine
mkdir_chroot /opt/lava/bin
copy_bin /usr/bin/updateEngine /opt/lava/bin
test_bin '/opt/lava/bin/updateEngine --help | grep "Linux A/B mode: Setting the current partition to bootable."'

# GUI
in_chroot 'apt install -y libfreetype6 libpaho-mqtt1.3 libglib2.0-0t64 libbluetooth3'
copy_bin /usr/bin/gui /opt/lava/bin/
validate_ldd '/opt/lava/bin/gui'

# kernel modules
copy_bin /lib/modules/io_manager.ko /opt/lava/modules/
copy_bin /lib/modules/bcmdhd.ko /opt/lava/modules/
copy_bin /lib/modules/chsc6540.ko /opt/lava/modules/

# wlan firmware
copy_bin /usr/lib/firmware/fw_bcm43438a1.bin /usr/lib/firmware/
copy_bin /usr/lib/firmware/nvram_ap6212a.txt /usr/lib/firmware/
mkdir -p "$ROOTFS_DIR/vendor/etc"
ln -sf /usr/lib/firmware "$ROOTFS_DIR/vendor/etc/firmware"

# lava_io
copy_bin /usr/bin/lava_io /opt/lava/bin/
validate_ldd '/opt/lava/bin/lava_io'
