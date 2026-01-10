#!/bin/bash

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

SUITE=trixie
PACKAGES="sudo,systemd-resolved,dbus,apt,ca-certificates,locales,systemd,systemd-sysv,udev,iproute2,iputils-ping,netbase,ifupdown,openssh-client,openssh-server,sudo,vim,less,procps"
MIRROR="https://deb.debian.org/debian"

CUR_DIR="$(realpath "$(dirname "$0")")"
ROOT_DIR="$(realpath "$(dirname "$0")/../../../..")"
ROOTFS_DIR="$(realpath "$1")"
DEBOOTSTRAP_DIR="$ROOT_DIR/tmp/debootstap-$(echo "$SUITE$PACKAGES" | sha256sum | awk '{print $1}')"

set -e

if [[ ! -d "$DEBOOTSTRAP_DIR" ]]; then
  echo ">> Bootstraping debian..."
  rm -rf "$DEBOOTSTRAP_DIR.tmp"
  debootstrap \
    --arch=arm64 \
    --foreign \
    --include="$PACKAGES" \
    "$SUITE" \
    "$DEBOOTSTRAP_DIR.tmp" \
    "$MIRROR"

  echo ">> Cleanup image..."
  rm -rf "$ROOT_DIR/etc/resolv.conf"

  echo ">> Second stage bootstrap..."
  "$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$DEBOOTSTRAP_DIR.tmp" /debootstrap/debootstrap --second-stage

  echo ">> Finalizing bootstrap..."
  mv "$DEBOOTSTRAP_DIR.tmp" "$DEBOOTSTRAP_DIR"
fi

EXTRA_DEPS="libcurl4 wpasupplicant udev"

if [[ $(cat "$DEBOOTSTRAP_DIR/.deps" || true) != "$EXTRA_DEPS" ]]; then
  "$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$DEBOOTSTRAP_DIR" apt install -y $EXTRA_DEPS
  echo "$EXTRA_DEPS" > "$DEBOOTSTRAP_DIR/.deps"
fi

if [[ ! -d "${ROOTFS_DIR}.org" ]]; then
  echo ">> Backuping rootfs..."
  mv "$ROOTFS_DIR"{,.org}
else
  echo ">> Cleaning rootfs..."
  rm -rf "$ROOTFS_DIR"
fi

echo ">> Copying bootstrap..."
cp -r "$DEBOOTSTRAP_DIR" "$ROOTFS_DIR"

echo ">> Creating required directories..."
mkdir -p "$ROOTFS_DIR/"{overlay,system,rom,oem,userdata}

echo ">> Enabling multi-user.target as default..."
"$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$ROOTFS_DIR" systemctl set-default graphical.target

echo ">> Installing systemd-resolved..."
"$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$ROOTFS_DIR" systemctl enable systemd-resolved
ln -sf /run/systemd/resolve/stub-resolv.conf "$ROOTFS_DIR/etc/resolv.conf"

# echo ">> Enable volatile storage..."
# echo "volatile=state" > "$ROOTFS_DIR/etc/systemd/volatile.conf"

echo ">> Set root password..."
"$ROOT_DIR/scripts/helpers/chroot_firmware.sh" "$ROOTFS_DIR" bash -c "echo root:snapmaker | chpasswd"

echo ">> Debian Bootstrap installed to $ROOTFS_DIR"
