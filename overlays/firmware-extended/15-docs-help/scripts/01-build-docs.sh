#!/bin/bash

if [[ -z "$CREATE_FIRMWARE" ]]; then
  echo "Error: This script should be run within the create_firmware.sh environment."
  exit 1
fi

set -eo pipefail

export BUNDLE_PATH="$CACHE_DIR/bundle"

echo ">> Building documentation site..."
cd "$ROOT_DIR/docs"

if bundle install --quiet --local; then
  echo "[+] Bundle install completed using cached gems."
else
  echo "[*] Cached gems not found or incomplete. Installing gems from remote source..."
  bundle install
fi

bundle exec jekyll build --destination "$ROOTFS_DIR/usr/local/share/firmware-config/html/help" --baseurl "/firmware-config/help"

echo "[+] Documentation built successfully"
