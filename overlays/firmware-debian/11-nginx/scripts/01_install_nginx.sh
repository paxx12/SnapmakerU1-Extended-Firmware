#!/bin/bash

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"
ROOTFS_DIR="$(realpath "$1")"

set -e

in_chroot() {
  "$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$ROOTFS_DIR" bash -c "$@"
}

echo ">> Enabling nginx service..."
in_chroot 'systemctl enable nginx'

echo ">> Create /var/log/nginx directory"
in_chroot 'mkdir -p /var/log/nginx && chown www-data:www-data /var/log/nginx && chmod 755 /var/log/nginx'

echo ">> Remove sites-enabled/default"
rm -f "$ROOTFS_DIR/etc/nginx/sites-enabled/default"

echo ">> Nginx installation complete"
