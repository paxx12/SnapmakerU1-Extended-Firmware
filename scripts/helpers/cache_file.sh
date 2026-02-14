#!/usr/bin/env bash

if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "Usage: $0 <dep-name> <cache-file> [extract-dir]"
  exit 1
fi

DEP_NAME="$1"
CACHE_FILE="$2"
EXTRACT_DIR="$3"

set -e

source "$(dirname "$0")/../../deps.mk"

DEP_NAME="${DEP_NAME^^}"
DEP_NAME="${DEP_NAME//-/_}"
FILE_URL_VAR="${DEP_NAME}_FILE_URL"
FILE_SHA256_VAR="${DEP_NAME}_FILE_SHA256"
FILE_URL="${!FILE_URL_VAR}"
FILE_SHA256="${!FILE_SHA256_VAR}"

if [[ -z "$FILE_URL" || -z "$FILE_SHA256" ]]; then
  echo "Error: File URL or SHA256 not found for dependency $DEP_NAME"
  exit 1
fi

echo ">> File URL: $FILE_URL, SHA256: $FILE_SHA256"

CACHE_DIR="$(dirname "$CACHE_FILE")"
FILENAME="$(basename "$CACHE_FILE")"

mkdir -p "$CACHE_DIR"

if [[ ! -f "$CACHE_FILE" ]]; then
  echo ">> Downloading $FILENAME..."
  wget -O "$CACHE_FILE" "$FILE_URL"
fi

echo ">> Verifying $CACHE_FILE checksum..."
if ! echo "$FILE_SHA256  $CACHE_FILE" | sha256sum --check --status; then
  echo "[!] SHA256 checksum mismatch for $FILENAME, re-downloading..."
  rm -f "$CACHE_FILE"
  wget -O "$CACHE_FILE" "$FILE_URL"
  echo ">> Verifying $CACHE_FILE checksum..."
  if ! echo "$FILE_SHA256  $CACHE_FILE" | sha256sum --check --status; then
    echo "[!] SHA256 checksum mismatch after re-download for $FILENAME"
    exit 1
  fi
fi

if [[ -z "$EXTRACT_DIR" ]]; then
  exit 0
fi

rm -rf "$EXTRACT_DIR"
mkdir -p "$EXTRACT_DIR"

case "$FILENAME" in
  *.tar.gz)
    echo ">> Extracting $FILENAME..."
    tar -xzf "$CACHE_FILE" -C "$EXTRACT_DIR"
    ;;

  *.tar.xz)
    echo ">> Extracting $FILENAME..."
    tar -xJf "$CACHE_FILE" -C "$EXTRACT_DIR"
    ;;

  *.zip)
    echo ">> Extracting $FILENAME..."
    unzip -o "$CACHE_FILE" -d "$EXTRACT_DIR"
    ;;

  *)
    ;;
esac
