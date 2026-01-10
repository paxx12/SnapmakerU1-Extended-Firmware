#!/bin/bash

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"
ROOTFS_DIR="$(realpath "$1")"
ORG_ROOTFS_DIR="${ROOTFS_DIR}.org"

set -e

mkdir_chroot() {
  for dir; do
    echo ">> Creating directory $dir in chroot..."
    mkdir -p "$ROOTFS_DIR/$dir"
  done
}

copy_chroot() {
  local target="$1"
  shift

  echo ">> Copying to $target the $@..."
  for src; do
    cp -rv -L --remove-destination "$ORG_ROOTFS_DIR/$src" "$ROOTFS_DIR/$target"
  done
}

in_chroot() {
  "$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$ROOTFS_DIR" bash -c "$@"
}

echo ">> Copying Klipper from /home/lava/klipper to /opt/klipper..."
mkdir_chroot /opt/klipper
copy_chroot /opt/klipper/ /home/lava/klipper/.

echo ">> Applying patches to klipper..."
cat <<'EOF' | in_chroot 'cd /opt/klipper && patch -p1'
--- a/scripts/klippy-requirements.txt
+++ b/scripts/klippy-requirements.txt
@@ -2,10 +2,11 @@
 # the Klipper host software (Klippy).  These package requirements are
 # typically installed via the command:
 #   pip install -r klippy-requirements.txt
-cffi==1.14.6
+cffi==1.17.0
 pyserial==3.4
 greenlet==2.0.2 ; python_version < '3.12'
-greenlet==3.0.3 ; python_version >= '3.12'
+greenlet==3.0.3 ; python_version >= '3.12' and python_version < '3.13'
+greenlet==3.3.0 ; python_version >= '3.13'
 Jinja2==2.11.3
 python-can==3.3.4
 markupsafe==1.1.1
EOF

echo ">> Creating virtual environment in /opt/klipper..."
in_chroot 'python3 -m venv /opt/klipper/venv'

echo ">> Installing klipper requirements..."
in_chroot '/opt/klipper/venv/bin/pip3 install --upgrade pip'
in_chroot '/opt/klipper/venv/bin/pip3 install -r /opt/klipper/scripts/klippy-requirements.txt'

# Additional modules not included in klippy-requirements.txt
echo ">> Installing additional klipper requirements..."
in_chroot '/opt/klipper/venv/bin/pip3 install paho-mqtt spidev cryptography "numpy<2.0"'

echo ">> Setting ownership to lava:lava..."
in_chroot 'chown -R lava:lava /opt/klipper'

echo ">> Klipper installation complete"
