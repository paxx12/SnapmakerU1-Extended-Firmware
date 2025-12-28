#!/bin/bash

if [[ $# -ne 2 ]]; then
  echo "usage: $0 <user@ip> <profile>"
  exit 1
fi

SSH_HOST="$1"
PROFILE="$2"
shift 2

set -xe

rm -rf "firmware/firmware_$PROFILE.bin" "tmp/firmware"
make build OUTPUT_FILE=firmware/firmware_$PROFILE.bin PROFILE="$PROFILE"
scp "tmp/firmware/update.img" "$SSH_HOST:/tmp/"
ssh "$SSH_HOST" /home/lava/bin/systemUpgrade.sh upgrade soc /tmp/update.img