#!/usr/bin/env bash

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <upgrade.bin> <temp-dir> <output.bin> [overlays...]"
  exit 1
fi

set -eo pipefail

IN_FIRMWARE="$(realpath "$1")"
TEMP_DIR="$(realpath -m "$2")"
OUT_FIRMWARE="$(realpath -m "$3")"
ROOT_DIR="$(realpath "$(dirname "$0")/..")"
shift 3

rm -rf "$TEMP_DIR"

echo ">> Unpacking firmware..."
"$ROOT_DIR/scripts/helpers/unpack_firmware.sh" "$IN_FIRMWARE" "$TEMP_DIR"

echo ">> Extracting squashfs from rootfs.img..."
unsquashfs -d "$TEMP_DIR/rootfs" "$TEMP_DIR/rk-unpacked/rootfs.img"

echo ">> Add kernel modules to rootfs..."
"$ROOT_DIR/scripts/helpers/compile_kernel_modules.sh" "$TEMP_DIR/rootfs/info/config-6.1" "$ROOT_DIR/tmp/kernel" "$TEMP_DIR/rootfs/lib/modules/"

for overlay; do
  echo ">> Applying overlay $overlay..."
  if [[ -d "$overlay/patches/" ]]; then
    for patchfile in "$overlay/patches/"*.patch; do
      echo "[+] Applying patch: $(basename "$patchfile")"
      patch -d "$TEMP_DIR/rootfs" -p1 < "$patchfile"
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
    cp -rv "$overlay/root/." "$TEMP_DIR/rootfs/"
  fi
done

echo ">> Create squash filesystem..."
mksquashfs "$TEMP_DIR/rootfs" "$TEMP_DIR/rk-unpacked/rootfs-v2.img" -comp gzip

echo ">> Replace rootfs.img in firmware..."
mv -v "$TEMP_DIR/rk-unpacked"/{rootfs-v2,rootfs}.img

echo ">> Update version..."
git rev-parse --short HEAD >> "$TEMP_DIR/UPFILE_VERSION"

echo ">> Repacking firmware..."
"$ROOT_DIR/scripts/helpers/pack_firmware.sh" "$TEMP_DIR" "$OUT_FIRMWARE"

echo ">> Done: $OUT_FIRMWARE"
