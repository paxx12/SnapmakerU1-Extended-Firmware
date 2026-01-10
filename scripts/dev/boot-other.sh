#!/bin/bash

if [[ $# -ne 2 ]]; then
  echo "usage: $0 <user@ip> <profile>"
  exit 1
fi

SSH_HOST="$1"
PROFILE="$2"
shift 2

set -xe

sshpass -p snapmaker ssh -t "$SSH_HOST" sudo /opt/lava/updateEngine --misc=other --reboot
