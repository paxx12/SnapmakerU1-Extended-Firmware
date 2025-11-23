#!/bin/bash

if [[ $# -ne 2 ]]; then
  echo "usage: $0 <user@ip> <basic|extended>"
  exit 1
fi

set -xe

rm -f "firmware/firmware_$2.bin"
make "${2}_firmware"
scp "tmp/$2/update.img" "$1:/tmp/"
ssh "$1" /home/lava/bin/systemUpgrade.sh upgrade soc /tmp/update.img
