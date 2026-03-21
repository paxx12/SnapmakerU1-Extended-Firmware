#!/usr/bin/env bash

set -e

IMAGE_NAME="snapmaker-u1-dev"
BUILD_CONTEXT=".github/dev"

# See https://docs.docker.com/build/building/multi-platform/
if ! docker buildx build --platform linux/arm64 --cache-from "$IMAGE_NAME" -t "$IMAGE_NAME" --load "$BUILD_CONTEXT"; then
    echo "[!] Docker build failed."
    exit 1
fi

TTY_FLAG=""
[[ -t 0 ]] && TTY_FLAG="-it"

ENV_FLAGS="-e GIT_VERSION -e CI -e PASSWORD"

exec docker run --platform linux/arm64 --rm $TTY_FLAG $ENV_FLAGS -w "$PWD" -v "$PWD:$PWD" --entrypoint /bin/bash "$IMAGE_NAME"
