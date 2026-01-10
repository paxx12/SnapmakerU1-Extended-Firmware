#!/bin/bash

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"
ROOTFS_DIR="$(realpath "$1")"
ORG_ROOTFS_DIR="${ROOTFS_DIR}.org"

set -e

mkdir_chroot() {
  for dir; do
    echo ">> Creating directory $dir in chroot..."
    mkdir -p "$ROOTFS_DIR/$dir"
  done
}

copy_chroot() {
  local target="$1"
  shift

  echo ">> Copying to $target the $@..."
  for src; do
    cp -rv -L --remove-destination "$ORG_ROOTFS_DIR/$src" "$ROOTFS_DIR/$target"
  done
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

# copy all lib
mkdir_chroot /opt/lava/lib
copy_chroot /opt/lava/lib /usr/lib/librkwifibt.so
copy_chroot /opt/lava/lib /usr/lib/libzlog.so.1.2
copy_chroot /opt/lava/lib /usr/lib/libjpeg.so.8
copy_chroot /opt/lava/lib /usr/lib/libwpa_client.so

# updateEngine
mkdir_chroot /opt/lava/bin
copy_chroot /opt/lava/bin /usr/bin/updateEngine
test_bin '/opt/lava/bin/updateEngine --help | grep "Linux A/B mode: Setting the current partition to bootable."'

# GUI
in_chroot 'apt install -y libfreetype6 libpaho-mqtt1.3 libglib2.0-0t64 libbluetooth3'
copy_chroot /opt/lava/bin /usr/bin/gui
validate_ldd '/opt/lava/bin/gui'

# GUI resources
mkdir_chroot /home/lava/resource
copy_chroot /home/lava/resource/ /home/lava/resource/.

# kernel modules
mkdir_chroot /opt/lava/modules
copy_chroot /opt/lava/modules /lib/modules/io_manager.ko
copy_chroot /opt/lava/modules /lib/modules/bcmdhd.ko
copy_chroot /opt/lava/modules /lib/modules/chsc6540.ko

# wlan firmware
mkdir_chroot /usr/lib/firmware
copy_chroot /usr/lib/firmware /usr/lib/firmware/fw_bcm43438a1.bin
copy_chroot /usr/lib/firmware /usr/lib/firmware/nvram_ap6212a.txt
mkdir -p "$ROOTFS_DIR/vendor/etc"
ln -sf /usr/lib/firmware "$ROOTFS_DIR/vendor/etc/firmware"

# lava_io
copy_chroot /opt/lava/bin /usr/bin/lava_io
validate_ldd '/opt/lava/bin/lava_io'
