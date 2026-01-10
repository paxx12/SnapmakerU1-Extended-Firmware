#!/bin/bash

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <user@ip>"
  exit 1
fi

SSH_HOST="$1"

set -xe

sshpass -p snapmaker ssh -t "$SSH_HOST" /opt/lava/bin/updateEngine --misc=other --reboot
