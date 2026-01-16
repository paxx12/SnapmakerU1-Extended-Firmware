#!/bin/bash

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

set -eo pipefail

echo ">> Installing screen-apps"
make -C "$ROOT_DIR/deps/screen-apps" install DESTDIR="$1"

echo ">> Installing Python dependencies for fb-http"
"$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$1" /usr/bin/pip3 install $(cat "$ROOT_DIR/deps/screen-apps/apps/fb-http/requirements.txt")
