#!/bin/bash

if [[ $# -ne 2 ]]; then
  echo "usage: $0 <user@ip> <profile>"
  exit 1
fi

SSH_HOST="$1"
PROFILE="$2"
shift 2

set -xe

ROOT_DIR="$(dirname "$0")/../.."
OVERLAY_ROOT_DIRS="$ROOT_DIR/overlays/firmware-$PROFILE"/*/root/.

sshpass -p snapmaker scp -r $OVERLAY_ROOT_DIRS "$SSH_HOST":/
