#!/bin/bash

set -e

echo ">> Creating required directories..."
mkdir -p /{overlay,rom,oem,userdata}

echo ">> Enabling multi-user.target as default..."
systemctl set-default multi-user.target

echo ">> Disabling systemd-networkd-wait-online.service..."
systemctl mask systemd-networkd-wait-online.service

echo ">> Installing systemd-resolved..."
systemctl enable systemd-resolved
ln -sf /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf
