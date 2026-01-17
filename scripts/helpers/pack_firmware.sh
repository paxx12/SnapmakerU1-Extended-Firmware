#!/usr/bin/env bash

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <input_dir> <output.bin>"
  exit 1
fi

set -eo pipefail

if [[ ! -d "$1" ]]; then
  echo "Error: Input directory $1 does not exist."
  exit 1
fi

if [[ -f "$2" ]] && [[ -z "$FORCE" ]]; then
  echo "Error: Output file $2 already exists."
  exit 1
fi

IN_DIR="$(realpath "$1")"
OUT="$(realpath -m "$2")"
ROOT_DIR="$(realpath "$(dirname "$0")/../..")"

cd "$IN_DIR"

echo ">> Repacking rk-rom.new.img"
"$ROOT_DIR/tools/rk2918_tools/afptool" -pack rk-unpacked rk-rom.new.img

echo ">> Repacking update.img"
"$ROOT_DIR/tools/rk2918_tools/img_maker" rk-loader.img rk-rom.new.img update.img

echo ">> Repacking output firmware"
"$ROOT_DIR/tools/upfile/upfile" pack "$OUT"

echo ">> Done. Output written to $OUT"
