#!/usr/bin/env bash

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 <target-dir> <git-url> <git-rev>"
  exit 1
fi

TARGET_DIR="$1"
GIT_URL="$2"
GIT_SHA="$3"

set -e

if [[ ! -d "$TARGET_DIR" ]]; then
  echo ">> Cloning $GIT_URL into $TARGET_DIR"
  git clone "$GIT_URL" "$TARGET_DIR" --recursive
elif [[ -z "$FORCE" ]]; then
  echo ">> Using cached git repository in $TARGET_DIR"
  exit 0
elif [[ "$CI" == "true" ]]; then
  echo ">> CI environment detected. Forcing the git repository to be re-fetched."
fi

echo ">> Fetching $GIT_SHA into $TARGET_DIR"
if ! git -C "$TARGET_DIR" checkout "$GIT_SHA"; then
  git fetch origin "$GIT_SHA"
  git -C "$TARGET_DIR" checkout -f "$GIT_SHA"
fi

git -C "$TARGET_DIR" submodule update --init --recursive
