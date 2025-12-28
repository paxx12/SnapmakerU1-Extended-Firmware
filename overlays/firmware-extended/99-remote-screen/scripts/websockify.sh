#!/bin/bash

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"

GIT_URL=https://github.com/novnc/websockify.git

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

set -eo pipefail

TARGET_DIR="$ROOT_DIR/tmp/websockify"

if [[ ! -d "$TARGET_DIR" ]]; then
  git clone --depth 1 --branch v0.13.0 "$GIT_URL" "$TARGET_DIR"
fi

echo ">> Setting up cross-compilation environment..."
export CROSS_COMPILE=aarch64-linux-gnu-
export CC="${CROSS_COMPILE}gcc"
export CXX="${CROSS_COMPILE}g++"
export AR="${CROSS_COMPILE}ar"
export RANLIB="${CROSS_COMPILE}ranlib"
export STRIP="${CROSS_COMPILE}strip"

echo ">> Compiling rebind.so for websockify wrap mode..."
make -C "$TARGET_DIR"

echo ">> Installing websockify (Python application)..."

# Create installation directories
INSTALL_DIR="$1/usr/local/share/websockify"
BIN_DIR="$1/usr/local/bin"

mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

# Copy websockify Python module
cp -r "$TARGET_DIR/websockify" "$INSTALL_DIR/"
cp "$TARGET_DIR/run" "$INSTALL_DIR/"
cp "$TARGET_DIR/rebind.so" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/run"

# Create wrapper script in /usr/local/bin
cat > "$BIN_DIR/websockify" << 'EOF'
#!/bin/sh
cd /usr/local/share/websockify
exec python3 -m websockify "$@"
EOF

chmod +x "$BIN_DIR/websockify"

echo "Done."
