#!/usr/bin/env bash
#
# Variant of ./dev.sh for environments where Docker bind-mounts silently
# remap file ownership (notably Docker Desktop on Windows/macOS, and some
# WSL setups). The squashfs unpack/repack performed by `make build` must
# preserve UID 0 (root) for files like /etc/passwd; bind-mount UID remapping
# breaks that and produces unbootable rootfs images.
#
# This script is identical to ./dev.sh except that tmp/ is mounted as a
# Docker named volume instead of a host bind-mount. The named volume lives
# on a real Linux ext4 filesystem inside Docker's storage, so ownership is
# preserved correctly.
#
# Side effect: contents of tmp/ are NOT visible from the host. To inspect:
#   ./dev-local.sh bash   # then explore tmp/ inside the container
# To wipe build state:
#   ./dev-local.sh clean-tmp
#
# Native Linux Docker users should prefer ./dev.sh.

set -e

IMAGE_NAME="snapmaker-u1-dev"
BUILD_CONTEXT=".github/dev"

if ! docker build --cache-from "$IMAGE_NAME" -t "$IMAGE_NAME" "$BUILD_CONTEXT"; then
    echo "[!] Docker build failed."
    exit 1
fi

TTY_FLAG=""
[[ -t 0 ]] && TTY_FLAG="-it"

ENV_FLAGS="-e GIT_VERSION -e CI -e PASSWORD"

TMP_VOLUME="snapmaker-u1-tmp"
mkdir -p tmp

# `./dev-local.sh clean-tmp` — wipe the named tmp volume. This is needed when
# the host path of the workspace changes (e.g. switching between ./dev.sh and
# ./dev-local.sh, or moving the repo), because cached CMake build trees
# embed absolute paths and refuse to be reused from a different mount point.
if [[ "${1:-}" == "clean-tmp" ]]; then
    docker volume rm "$TMP_VOLUME" 2>/dev/null || true
    echo "[+] Removed Docker volume: $TMP_VOLUME"
    exit 0
fi

exec docker run --rm $DOCKER_OPTS $TTY_FLAG $ENV_FLAGS --cap-add=SYS_ADMIN \
    -w "$PWD" \
    -v "$PWD:$PWD" \
    -v "$TMP_VOLUME:$PWD/tmp" \
    "$IMAGE_NAME" "$@"
