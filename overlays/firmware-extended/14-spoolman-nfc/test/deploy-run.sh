#!/usr/bin/env bash

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <printer-ip-or-host>"
  echo "Example: $0 192.168.1.100"
  exit 1
fi

SSH_HOST="$1"
DIR="$(dirname "$0")"
ROOT_DIR="$(realpath "$DIR/../../../..")"

set -xeo pipefail

echo "Deploying modified files to $SSH_HOST..."

# Copy modified Klipper file
scp "$ROOT_DIR/tmp/firmware/rootfs/home/lava/klipper/klippy/extras/filament_protocol.py" "root@$SSH_HOST:/home/lava/klipper/klippy/extras/"

# Copy modified Moonraker component
scp "$ROOT_DIR/tmp/firmware/rootfs/home/lava/moonraker/moonraker/components/spoolman.py" "root@$SSH_HOST:/home/lava/moonraker/moonraker/components/"

# Restart Klipper and Moonraker services on the printer
echo "Restarting Klipper and Moonraker services..."
ssh -t "root@$SSH_HOST" "/etc/init.d/S60klipper restart && /etc/init.d/S61moonraker restart"

echo "Deployed successfully!"
