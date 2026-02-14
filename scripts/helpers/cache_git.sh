#!/usr/bin/env bash

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <dependency-name> <target-dir>"
  exit 1
fi

DEP_NAME="$1"
TARGET_DIR="$2"

set -e

source "$(dirname "$0")/../../deps.mk"

# replace - to uppercase and _ to -
DEP_NAME="${DEP_NAME^^}"
DEP_NAME="${DEP_NAME//-/_}"
GIT_NAME_VAR="${DEP_NAME}_GIT_URL"
GIT_SHA256_VAR="${DEP_NAME}_GIT_SHA256"
GIT_URL="${!GIT_NAME_VAR}"
GIT_SHA256="${!GIT_SHA256_VAR}"

if [[ -z "$GIT_URL" || -z "$GIT_SHA256" ]]; then
  echo "Error: Git URL or SHA256 not found for dependency $DEP_NAME"
  exit 1
fi

echo ">> Git URL: $GIT_URL, SHA256: $GIT_SHA256"

if [[ -n "$CI" ]]; then
  echo ">> CI environment detected. Forcing the git repository to be re-fetched."
  git init "$TARGET_DIR"
elif [[ -d "$TARGET_DIR/.git" ]]; then
  echo ">> Using cached git repository in $TARGET_DIR"
  exit 0
else
  echo ">> Cloning $GIT_URL into $TARGET_DIR"
  git clone "$GIT_URL" "$TARGET_DIR"
fi

echo ">> Fetching $GIT_SHA256 into $TARGET_DIR"
if ! git -C "$TARGET_DIR" checkout -f "$GIT_SHA256"; then
  git -C "$TARGET_DIR" remote set-url origin "$GIT_URL" || git -C "$TARGET_DIR" remote add origin "$GIT_URL"
  git -C "$TARGET_DIR" fetch origin "$GIT_SHA256"
  git -C "$TARGET_DIR" checkout -f "$GIT_SHA256"
fi

git -C "$TARGET_DIR" submodule update --init --recursive --checkout --force
