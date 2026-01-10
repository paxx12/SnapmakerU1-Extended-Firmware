#!/bin/bash

set -e

apt-get purge -t bookworm -y \
  build-essential \
  cpp-14-aarch64-linux-gnu \
  gcc-14-aarch64-linux-gnu \
  g++-14-aarch64-linux-gnu \
  libpython3.11-dev \
  libgcc-14-dev \
  vim-runtime \
  git

apt-get autoremove -y

rm -rf "/var/cache/apt/"
rm -rf "/var/lib/apt/lists/"
find "/var/log" -type f -delete
rm -rf "/tmp/"*
rm -rf "/usr/share/locale/"
rm -rf "/etc/machine-id"
