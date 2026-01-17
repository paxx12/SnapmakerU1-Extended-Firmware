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
scp "tmp/firmware/rk-unpacked/boot.img" "$SSH_HOST:/tmp/"
ssh "$SSH_HOST" dd if=/tmp/boot.img of=/dev/block/by-name/boot_a bs=4M conv=fsync
ssh "$SSH_HOST" reboot
