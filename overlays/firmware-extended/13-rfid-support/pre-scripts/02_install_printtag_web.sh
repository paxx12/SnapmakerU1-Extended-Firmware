#!/usr/bin/env bash

if [[ -z "$CREATE_FIRMWARE" ]]; then
  echo "Error: This script should be run within the create_firmware.sh environment."
  exit 1
fi

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

set -eo pipefail

PRINTTAG_WEB_URL=https://github.com/paxx12/PrintTag-Web.git
PRINTTAG_WEB_SHA=2e2d83139d6818365b4b66a8c891ba0b461a63f2

# Pin exact versions for reproducible builds.
PICKR_VERSION=1.9.1
PICKR_CSS_FILENAME=pickr-${PICKR_VERSION}-nano.min.css
PICKR_JS_FILENAME=pickr-${PICKR_VERSION}.min.js
PICKR_CSS_URL=https://cdn.jsdelivr.net/npm/@simonwep/pickr@${PICKR_VERSION}/dist/themes/nano.min.css
PICKR_JS_URL=https://cdn.jsdelivr.net/npm/@simonwep/pickr@${PICKR_VERSION}/dist/pickr.min.js
PICKR_CSS_SHA256=cb9f82b125cc07d58bc12aac6e936f8582751c56fed3353b1d1310cf76a67a4b
PICKR_JS_SHA256=f42fb8ba223e1283a68b17b9b510fc8738977ed680e6506155e1796e3bedaa46

DEST="$1/home/lava/www/rfid-manager/lib"

echo ">> Cloning PrintTag-Web at $PRINTTAG_WEB_SHA..."
cache_git.sh "$CACHE_DIR/PrintTag-Web" "$PRINTTAG_WEB_URL" "$PRINTTAG_WEB_SHA"

echo ">> Installing PrintTag-Web JS libraries..."
mkdir -p "$DEST/PrintTag-Web"
cp "$CACHE_DIR/PrintTag-Web/public/ndef.js" "$DEST/PrintTag-Web/"
cp "$CACHE_DIR/PrintTag-Web/public/openspool.js" "$DEST/PrintTag-Web/"

echo ">> Downloading Pickr ${PICKR_VERSION}..."
cache_file.sh "$CACHE_DIR/$PICKR_CSS_FILENAME" "$PICKR_CSS_URL" "$PICKR_CSS_SHA256"
cache_file.sh "$CACHE_DIR/$PICKR_JS_FILENAME" "$PICKR_JS_URL" "$PICKR_JS_SHA256"

echo ">> Installing Pickr ${PICKR_VERSION}..."
mkdir -p "$DEST/pickr"
cp "$CACHE_DIR/$PICKR_CSS_FILENAME" "$DEST/pickr/nano.min.css"
cp "$CACHE_DIR/$PICKR_JS_FILENAME" "$DEST/pickr/pickr.min.js"
