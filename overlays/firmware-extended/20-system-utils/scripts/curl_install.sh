#!/bin/env bash

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

set -eo pipefail

printf ">> Installing latest curl from precompiled tarball\n"

REPO_URL=https://github.com/stunnel/static-curl
CURL_VERSION=8.17.0
CURL_SHA256=fa8d1db2f1651d94cdb061ede60f20b895edd31439d8e2eb25383606117c7316

# Example aarch64 tarball name: curl-linux-aarch64-glibc-8.17.0.tar.xz
# Tarball content is always the same: "curl" and "SHA256SUMS"

TARBALL_NAME="curl-linux-aarch64-glibc-${CURL_VERSION}.tar.xz"
DOWNLOAD_URL="$REPO_URL/releases/download/${CURL_VERSION}/$TARBALL_NAME"
TARGET_DIR="$ROOT_DIR/tmp/system-utils/curl"
OUTPUT_TARBALL="$TARGET_DIR/$TARBALL_NAME"

if [ ! -d "$TARGET_DIR" ]; then
	if ! mkdir -p "$TARGET_DIR"; then
		printf "Error: Failed to create directory %s\n" "$TARGET_DIR"
		exit 1
	fi
fi

function download_and_extract_tarball() {
	# Download tarball and extract to target dir
	rm -rf "${TARGET_DIR:?}"/* 2>/dev/null
	printf "Downloading %s from %s...\n" "$TARBALL_NAME" "$DOWNLOAD_URL"
	if ! curl -LSsf -o "$OUTPUT_TARBALL" "$DOWNLOAD_URL"; then
		printf "Error: Failed to download %s\n" "$DOWNLOAD_URL"
		rm -f "$OUTPUT_TARBALL"
		return 1
	fi
	if ! tar -xf "$OUTPUT_TARBALL" -C "$TARGET_DIR"; then
		printf "Error: Failed to extract tarball %s\n" "$OUTPUT_TARBALL"
		rm -f "$OUTPUT_TARBALL"
		return 1
	fi
}

function verify_checksum() {
	# Verify SHA256SUMS file contains our expected checksum, then verify binary
	if [ ! -f "$TARGET_DIR/SHA256SUMS" ] || [ ! -f "$TARGET_DIR/curl" ]; then
		return 1
	fi
	# First verify SHA256SUMS contains our trusted checksum
	if ! grep -q "^$CURL_SHA256  curl$" "$TARGET_DIR/SHA256SUMS" 2>/dev/null; then
		return 1
	fi
	# Then verify the actual binary matches the SHA256SUMS file
	(cd "$TARGET_DIR" && sha256sum -c --strict --quiet SHA256SUMS 2>/dev/null) || return 1
}

# There is no cached curl binary, we need to download
if [ ! -f "${TARGET_DIR}/curl" ]; then
	if ! download_and_extract_tarball; then
		printf "Error: Initial download of curl tarball failed\n"
		exit 1
	fi
else
	printf "Using cached curl binary at %s/curl\n" "$TARGET_DIR"
fi

# Verify checksum of cached or newly downloaded binary
if ! verify_checksum; then
	printf "Curl binary checksum verification failed, re-downloading...\n"
	if ! download_and_extract_tarball; then
		printf "Error: Re-download failed\n"
		exit 1
	fi
	if ! verify_checksum; then
		printf "Error: Downloaded curl binary checksum verification failed.\n"
		exit 1
	fi
fi

# Ensure destination directory exists
if ! mkdir -p "$1/usr/local/bin/"; then
	printf "Error: Failed to create directory %s/usr/local/bin/\n" "$1"
	exit 1
fi

if ! cp "$TARGET_DIR/curl" "$1/usr/local/bin/"; then
	printf "Error: Failed to copy curl to %s/usr/local/bin/\n" "$1"
	exit 1
fi

if ! chown root:root "$1/usr/local/bin/curl"; then
	printf "Error: Failed to set ownership on %s/usr/local/bin/curl\n" "$1"
	exit 1
fi

if ! chmod 755 "$1/usr/local/bin/curl"; then
	printf "Error: Failed to set permissions on %s/usr/local/bin/curl\n" "$1"
	exit 1
fi

printf ">> curl installed to %s/usr/local/bin/curl\n" "$1"
