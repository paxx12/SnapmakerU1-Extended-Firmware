#!/bin/bash

set -e

echo ">> Uninstalling all current Python packages..."
apt-get remove -y python3* libpython3*
apt-get autoremove -y

echo ">> Adding bookworm repository to apt sources..."
echo "deb http://deb.debian.org/debian bookworm main" > /etc/apt/sources.list.d/bookworm.list
apt-get update

echo ">> Installing Python 3.11 and development headers from bookworm..."
apt-get install -t bookworm -y python3-dev python3.11-venv
python3.11 --version

# echo ">> Removing bookworm repository from apt sources..."
# rm -f /etc/apt/sources.list.d/bookworm.list
# apt-get update
