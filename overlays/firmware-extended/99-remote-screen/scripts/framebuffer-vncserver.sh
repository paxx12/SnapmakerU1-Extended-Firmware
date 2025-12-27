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
  
  # Patch touch.c to support multitouch coordinates (ABS_MT_POSITION_X/Y)
  PATCH_FILE="$(dirname "$0")/../framebuffer-vncserver-multitouch.patch"
  if [[ -f "$PATCH_FILE" ]]; then
    echo ">> Applying multitouch support patch..."
    patch -d "$TARGET_DIR" -p1 < "$PATCH_FILE"
  fi
  
  echo ">> Applying localhost binding patch..."
  patch -d "$TARGET_DIR" -p1 < "$ROOT_DIR/overlays/firmware-extended/99-remote-screen/framebuffer-vncserver-localhost.patch"
else
  # Reset any modifications to ensure clean state
  git -C "$TARGET_DIR" reset --hard "$GIT_SHA"
  
  # Patch touch.c to support multitouch coordinates (ABS_MT_POSITION_X/Y)
  PATCH_FILE="$(dirname "$0")/../framebuffer-vncserver-multitouch.patch"
  if [[ -f "$PATCH_FILE" ]]; then
    echo ">> Applying multitouch support patch..."
    patch -d "$TARGET_DIR" -p1 < "$PATCH_FILE"
  fi
  
  echo ">> Applying localhost binding patch..."
  patch -d "$TARGET_DIR" -p1 < "$ROOT_DIR/overlays/firmware-extended/99-remote-screen/framebuffer-vncserver-localhost.patch"
fi

echo ">> Setting up cross-compilation environment..."
export CROSS_COMPILE=aarch64-linux-gnu-
export CC="${CROSS_COMPILE}gcc"
export CXX="${CROSS_COMPILE}g++"
export AR="${CROSS_COMPILE}ar"
export RANLIB="${CROSS_COMPILE}ranlib"
export STRIP="${CROSS_COMPILE}strip"

echo ">> Compiling framebuffer-vncserver dependencies..."
rm -rf "$TARGET_DIR/build"
mkdir -p "$TARGET_DIR/build"

cmake -B "$TARGET_DIR/build" -S "$TARGET_DIR"

echo ">> Compiling framebuffer-vncserver..."
# make -C "$TARGET_DIR" install DESTDIR="$1"
make -C "$TARGET_DIR/build"
if [ ! -d "$1/usr/local/bin" ]; then
  mkdir -p "$1/usr/local/bin"
fi

cp "$TARGET_DIR/build/framebuffer-vncserver" "$1/usr/local/bin/framebuffer-vncserver"
chmod +x "$1/usr/local/bin/framebuffer-vncserver"

# Copy all required libraries recursively
build_env_lib_path=/usr/lib/aarch64-linux-gnu
target_lib_path=$1/usr/lib

echo ">> Resolving library dependencies recursively..."

# Function to get NEEDED libraries from a binary/library
get_needed_libs() {
	local file="$1"
	"${CROSS_COMPILE}readelf" -d "$file" 2>/dev/null | grep NEEDED | sed 's/.*\[\(.*\)\].*/\1/'
}

# Queue of files to process, starting with the main binary
declare -a to_process=("$TARGET_DIR/build/framebuffer-vncserver")
declare -A processed=()

while [[ ${#to_process[@]} -gt 0 ]]; do
	current="${to_process[0]}"
	to_process=("${to_process[@]:1}")  # Remove first element
	
	# Get needed libraries
	while read -r lib_name; do
		[[ -z "$lib_name" ]] && continue
		
		# Skip if already processed
		[[ -n "${processed[$lib_name]}" ]] && continue
		processed[$lib_name]=1
		
		# Check if library exists in target
		if [[ -f "$target_lib_path/$lib_name" ]]; then
			# Already in target, but still need to process its dependencies
			to_process+=("$target_lib_path/$lib_name")
		elif [[ -f "$build_env_lib_path/$lib_name" ]]; then
			# Copy from build environment
			echo ">> Copying $lib_name"
			cp -L "$build_env_lib_path/$lib_name" "$target_lib_path"
			# Add to queue to process its dependencies
			to_process+=("$target_lib_path/$lib_name")
		else
			echo ">> Warning: Library $lib_name not found"
		fi
	done < <(get_needed_libs "$current")
done

echo ">> framebuffer-vncserver installed to $1/usr/local/bin/framebuffer-vncserver"
