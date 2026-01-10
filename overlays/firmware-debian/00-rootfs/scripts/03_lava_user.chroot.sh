#!/bin/bash

set -e

if [[ ! -u "/usr/bin/sudo" ]]; then
  echo ">> Setting setuid bit on /usr/bin/sudo..."
  chmod u+s /usr/bin/sudo
fi

echo ">> Add user lava..."
useradd -m -G sudo,video,input,dialout -s /bin/bash lava
echo lava:snapmaker | chpasswd
