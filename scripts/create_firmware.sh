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

rm -rf "$TEMP_DIR"

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

echo ">> Unpacking firmware..."
"$ROOT_DIR/scripts/helpers/unpack_firmware.sh" "$IN_FIRMWARE" "$TEMP_DIR"

echo ">> Extracting squashfs from rootfs.img..."
unsquashfs -d "$TEMP_DIR/rootfs" "$TEMP_DIR/rk-unpacked/rootfs.img"

echo ">> Verifying ownership preservation..."
check_perms "$TEMP_DIR/rootfs/etc/passwd" 0 0
check_perms "$TEMP_DIR/rootfs/home/lava/bin/hwver.sh" 1000 1000
echo "   Ownership check passed"

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
    pushd "$overlay/patches/" > /dev/null
    # apply all .patch to their respective directories
    while read -r patchfile; do
      echo "[+] Applying patch: $(basename "$patchfile") in subdir $(dirname "$patchfile")"
      patch -F 0 -d "$TEMP_DIR/rootfs/$(dirname "$patchfile")" -p1 < "$patchfile"
    done < <(find -type f -name "*.patch")
    popd > /dev/null
  fi

  if [[ -d "$overlay/scripts/" ]]; then
    for scriptfile in "$overlay/scripts/"*.sh; do
      echo "[+] Running script: $(basename "$scriptfile")"
      ./"$scriptfile" "$TEMP_DIR/rootfs"
    done
  fi

  if [[ -d "$overlay/root/" ]]; then
    echo ">> Copying custom files..."
    cp -rv "$overlay/root/." "$TEMP_DIR/rootfs/"
  fi
done

echo ">> Checking for non-ARM binaries in rootfs..."
if FILES=$(find "$TEMP_DIR/rootfs" -type f -exec file {} + | grep "ELF" | grep -v "ARM"); then
  echo "!! Error: Found non-ARM binaries in the rootfs:"
  echo "$FILES"
  exit 1
fi

echo ">> Create squash filesystem..."
mksquashfs "$TEMP_DIR/rootfs" "$TEMP_DIR/rk-unpacked/rootfs-v2.img" -comp gzip

echo ">> Replace rootfs.img in firmware..."
mv -v "$TEMP_DIR/rk-unpacked"/{rootfs-v2,rootfs}.img

echo ">> Update version..."
git rev-parse --short HEAD >> "$TEMP_DIR/UPFILE_VERSION"

echo ">> Repacking firmware..."
"$ROOT_DIR/scripts/helpers/pack_firmware.sh" "$TEMP_DIR" "$OUT_FIRMWARE"

echo ">> Done: $OUT_FIRMWARE"
