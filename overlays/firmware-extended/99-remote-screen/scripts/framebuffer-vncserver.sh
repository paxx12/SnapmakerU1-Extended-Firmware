#!/bin/bash

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"

GIT_URL=https://github.com/ponty/framebuffer-vncserver.git
GIT_SHA=1963e57bebfde420baeecbb2c6848a2382488413

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

set -eo pipefail

TARGET_DIR="$ROOT_DIR/tmp/framebuffer-vncserver"

if [[ ! -d "$TARGET_DIR" ]]; then
  git clone "$GIT_URL" "$TARGET_DIR" --recursive
  if ! git -C "$TARGET_DIR" checkout "$GIT_SHA"; then
    git fetch origin "$GIT_SHA"
    git -C "$TARGET_DIR" checkout "$GIT_SHA"
  fi
else
  # Reset any modifications to ensure clean state
  git -C "$TARGET_DIR" reset --hard "$GIT_SHA"
fi

# Apply patches
OVERLAY_DIR="$ROOT_DIR/overlays/firmware-extended/99-remote-screen"
echo ">> Applying multitouch support patch..."
patch -d "$TARGET_DIR" -p1 < "$OVERLAY_DIR/framebuffer-vncserver-multitouch.patch"
echo ">> Applying localhost binding patch..."
patch -d "$TARGET_DIR" -p1 < "$OVERLAY_DIR/framebuffer-vncserver-localhost.patch"
echo ">> Applying static library dependencies patch..."
patch -d "$TARGET_DIR" -p1 < "$OVERLAY_DIR/framebuffer-vncserver-static-libs.patch"

echo ">> Setting up cross-compilation environment..."
export CROSS_COMPILE=aarch64-linux-gnu-
export CC="${CROSS_COMPILE}gcc"
export CXX="${CROSS_COMPILE}g++"
export AR="$(which ${CROSS_COMPILE}ar)"
export RANLIB="$(which ${CROSS_COMPILE}ranlib)"
export STRIP="${CROSS_COMPILE}strip"

# Build libvncserver statically (dependency of framebuffer-vncserver)
LIBVNC_GIT_URL=https://github.com/LibVNC/libvncserver.git
LIBVNC_GIT_SHA=9b54b1ec32731bd23158ca014dc18014db4194c3  # LibVNCServer-0.9.15
LIBVNC_DIR="$ROOT_DIR/tmp/libvncserver"
LIBVNC_INSTALL_DIR="$ROOT_DIR/tmp/libvncserver-static"

if [[ ! -d "$LIBVNC_INSTALL_DIR" ]]; then
  if [[ ! -d "$LIBVNC_DIR" ]]; then
    echo ">> Cloning libvncserver..."
    git clone "$LIBVNC_GIT_URL" "$LIBVNC_DIR"
    if ! git -C "$LIBVNC_DIR" checkout "$LIBVNC_GIT_SHA"; then
      git -C "$LIBVNC_DIR" fetch origin "$LIBVNC_GIT_SHA"
      git -C "$LIBVNC_DIR" checkout "$LIBVNC_GIT_SHA"
    fi
  else
    # Reset to ensure clean state
    git -C "$LIBVNC_DIR" reset --hard "$LIBVNC_GIT_SHA"
  fi
  
  echo ">> Building libvncserver ..."
  mkdir -p "$LIBVNC_DIR/build"
  cmake -B "$LIBVNC_DIR/build" -S "$LIBVNC_DIR" \
    -DCMAKE_INSTALL_PREFIX="$LIBVNC_INSTALL_DIR" \
    -DCMAKE_SYSTEM_NAME=Linux \
    -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
    -DCMAKE_C_COMPILER="${CC}" \
    -DCMAKE_CXX_COMPILER="${CXX}" \
    -DCMAKE_AR="${AR}" \
    -DCMAKE_RANLIB="${RANLIB}" \
    -DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER \
    -DBUILD_SHARED_LIBS=OFF \
    -DWITH_PNG=OFF \
    -DWITH_JPEG=OFF \
    -DWITH_OPENSSL=OFF \
    -DWITH_GNUTLS=OFF \
    -DWITH_THREADS=ON
  
  make -C "$LIBVNC_DIR/build" -j"$(nproc)"
  make -C "$LIBVNC_DIR/build" install
  
  echo ">> libvncserver static libraries installed to $LIBVNC_INSTALL_DIR"
fi

echo ">> Compiling framebuffer-vncserver dependencies..."
rm -rf "$TARGET_DIR/build"
mkdir -p "$TARGET_DIR/build"

cmake -B "$TARGET_DIR/build" -S "$TARGET_DIR" \
  -DCMAKE_PREFIX_PATH="$LIBVNC_INSTALL_DIR" \
  -DCMAKE_SYSTEM_NAME=Linux \
  -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_C_COMPILER="${CC}" \
  -DCMAKE_CXX_COMPILER="${CXX}" \
  -DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER

echo ">> Compiling framebuffer-vncserver..."
make -C "$TARGET_DIR/build"
if [ ! -d "$1/usr/local/bin" ]; then
  mkdir -p "$1/usr/local/bin"
fi

cp "$TARGET_DIR/build/framebuffer-vncserver" "$1/usr/local/bin/framebuffer-vncserver"
chmod +x "$1/usr/local/bin/framebuffer-vncserver"

echo ">> framebuffer-vncserver installed to $1/usr/local/bin/framebuffer-vncserver"
