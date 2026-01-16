#!/bin/bash

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

set -eo pipefail

echo ">> Installing Pillow for JPEG support"
stat "$1/usr/local/bin/fb-http.py" >/dev/null
stat "$1/usr/local/share/fb-http/html/index.html" >/dev/null
