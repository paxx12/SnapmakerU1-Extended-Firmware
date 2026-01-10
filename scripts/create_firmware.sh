#!/usr/bin/env bash

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <upgrade.bin> <temp-dir> <output.bin> [overlays...]"
  exit 1
fi

if [[ $(id -u) -ne 0 ]]; then
  echo "Error: This script must be run as root (sudo) - squashfs operations require root privileges"
  exit 1
fi

set -eo pipefail

IN_FIRMWARE="$(realpath "$1")"
TEMP_DIR="$(realpath -m "$2")"
OUT_FIRMWARE="$(realpath -m "$3")"
ROOT_DIR="$(realpath "$(dirname "$0")/..")"
shift 3

check_perms() {
  local file="$1"
  local expected_uid="$2"
  local expected_gid="$3"

  if [[ ! -e "$file" ]]; then
    echo "Error: $file does not exist for ownership check."
    exit 1
  fi

  local actual_uid=$(stat -c '%u' "$file")
  local actual_gid=$(stat -c '%g' "$file")

  if [[ "$actual_uid" != "$expected_uid" ]] || [[ "$actual_gid" != "$expected_gid" ]]; then
    echo "Error: $file should be $expected_uid:$expected_gid, got $actual_uid:$actual_gid"
    echo "This system does not properly preserve file ownership in squashfs operations."
    exit 1
  fi
}

if [[ -z "$DIRTY" ]]; then
  rm -rf "$TEMP_DIR"

  echo ">> Unpacking firmware..."
  "$ROOT_DIR/scripts/helpers/unpack_firmware.sh" "$IN_FIRMWARE" "$TEMP_DIR"

  echo ">> Extracting squashfs from rootfs.img..."
  unsquashfs -d "$TEMP_DIR/rootfs" "$TEMP_DIR/rk-unpacked/rootfs.img"

  echo ">> Verifying ownership preservation..."
  check_perms "$TEMP_DIR/rootfs/etc/passwd" 0 0
  check_perms "$TEMP_DIR/rootfs/home/lava/bin/hwver.sh" 1000 1000
  echo "   Ownership check passed"
fi

for overlay; do
  if [[ ! -d "$overlay" ]]; then
    echo "!! Overlay directory '$overlay' does not exist, skipping."
    exit 1
  fi

  echo ">> Applying overlay $overlay..."
  if [[ -d "$overlay/pre-scripts/" ]]; then
    for scriptfile in "$overlay/pre-scripts/"*.sh; do
      echo "[+] Running pre-scripts: $(basename "$scriptfile")"
      ./"$scriptfile" "$TEMP_DIR/rootfs"
    done
  fi

  if [[ -d "$overlay/patches/" ]]; then
    for patchfile in "$overlay/patches/"*.patch; do
      echo "[+] Applying patch: $(basename "$patchfile")"
      patch -F 0 -d "$TEMP_DIR/rootfs" -p1 < "$patchfile"
    done
  fi

  if [[ -d "$overlay/scripts/" ]]; then
    for scriptfile in "$overlay/scripts/"*.sh; do
      echo "[+] Running script: $(basename "$scriptfile")"
      ./"$scriptfile" "$TEMP_DIR/rootfs"
    done
  fi

  if [[ -d "$overlay/root/" ]]; then
    echo ">> Copying custom files..."
    cp -rv --remove-destination "$overlay/root/." "$TEMP_DIR/rootfs/"
  fi
done

if [[ -z "$DIRTY" ]]; then
  echo ">> Checking for non-ARM binaries in rootfs..."
  if FILES=$(find "$TEMP_DIR/rootfs" -type f -exec file {} + | grep "ELF" | grep -v "ARM"); then
    echo "!! Error: Found non-ARM binaries in the rootfs:"
    echo "$FILES"
    exit 1
  fi
fi

echo ">> Create squash filesystem..."
rm -rf "$TEMP_DIR/rk-unpacked/rootfs-v2.img"
mksquashfs "$TEMP_DIR/rootfs" "$TEMP_DIR/rk-unpacked/rootfs-v2.img" -comp gzip

echo ">> Checking image size..."
IMAGE_SIZE=$(stat -c '%s' "$TEMP_DIR/rk-unpacked/rootfs-v2.img")
MAX_SIZE=$((300 * 1024 * 1024))
if [[ $IMAGE_SIZE -gt $MAX_SIZE ]]; then
  echo "Error: Image size $(($IMAGE_SIZE / 1024 / 1024))MiB exceeds maximum of 300MiB"
  exit 1
fi
echo "   Image size: $(($IMAGE_SIZE / 1024 / 1024))MiB (OK)"

echo ">> Replace rootfs.img in firmware..."
mv -v "$TEMP_DIR/rk-unpacked"/{rootfs-v2,rootfs}.img

echo ">> Update version..."
git rev-parse --short HEAD >> "$TEMP_DIR/UPFILE_VERSION"

echo ">> Repacking firmware..."
"$ROOT_DIR/scripts/helpers/pack_firmware.sh" "$TEMP_DIR" "$OUT_FIRMWARE"

echo ">> Done: $OUT_FIRMWARE"
