#!/bin/bash

set -e

# trixie cleanup
apt-get autopurge -y \
  build-essential \
  cpp-14-aarch64-linux-gnu \
  gcc-14-aarch64-linux-gnu \
  g++-14-aarch64-linux-gnu \
  libgcc-14-dev \
  vim-runtime \
  git

# bookworm cleanup
apt-get autoremove -y libpython3.11-dev

# general cleanup
rm -rf "/var/cache/apt/"
rm -rf "/var/lib/apt/lists/"
find "/var/log" -type f -delete
rm -rf "/tmp/"*
rm -rf "/usr/share/locale/"
rm -rf "/etc/machine-id"
