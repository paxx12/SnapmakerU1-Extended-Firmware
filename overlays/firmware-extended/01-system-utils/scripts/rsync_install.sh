#!/usr/bin/env bash

set -eo pipefail

if [[ -z "$CREATE_FIRMWARE" ]]; then
  echo "Error: This script should be run within the create_firmware.sh environment."
  exit 1
fi

# Cross-compile rsync for aarch64 from the Debian upstream source tarball.
# The previous binary (Samba CentOS 8 aarch64) was linked against OpenSSL 1.1
# (libcrypto.so.1.1), which is absent from the Snapmaker U1 (OpenSSL 3 only).
# We now compile rsync against OpenSSL 3 using the aarch64 cross-toolchain that
# is already present in the build Docker image.
# See: https://github.com/paxx12/SnapmakerU1-Extended-Firmware/issues/154

# Debian upstream source for rsync 3.4.1 (+ds1 = Debian-stripped orig tarball).
# SHA256 sourced from: https://ftp.debian.org/debian/pool/main/r/rsync/rsync_3.4.1+ds1-5+deb13u1.dsc
VERSION=3.4.1+ds1
FILENAME="rsync_${VERSION}.orig.tar.xz"
URL="https://ftp.debian.org/debian/pool/main/r/rsync/$FILENAME"
SRC_SHA256=bb9e2dda7e79d9639bc04bdafff6bb0b06a606ed915358b574696384215c9e5c

cache_file.sh "$CACHE_DIR/$FILENAME" "$URL" "$SRC_SHA256"

BUILDDIR="$BUILD_DIR/rsync-src"
rm -rf "$BUILDDIR"
mkdir -p "$BUILDDIR"

echo ">> Extracting rsync source..."
tar -xJf "$CACHE_DIR/$FILENAME" -C "$BUILDDIR"

SRC=$(ls -d "$BUILDDIR"/rsync-*)

echo ">> Cross-compiling rsync for aarch64..."
(
  cd "$SRC"
  ./configure \
    --host=aarch64-linux-gnu \
    CC=aarch64-linux-gnu-gcc \
    CFLAGS="-O2 -I/usr/include/aarch64-linux-gnu" \
    LDFLAGS="-L/usr/lib/aarch64-linux-gnu" \
    --with-openssl \
    --without-zstd \
    --without-lz4 \
    --without-xxhash \
    --disable-debug
  make -j"$(nproc)" rsync
)

install -d "$ROOTFS_DIR/usr/local/bin"
install -m 755 "$SRC/rsync" "$ROOTFS_DIR/usr/local/bin/rsync"

echo ">> rsync installed successfully ($(file "$ROOTFS_DIR/usr/local/bin/rsync"))"
