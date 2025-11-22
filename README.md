# Snapmaker U1 Firmware Tools

Tools for extracting, modifying, and rebuilding Snapmaker U1 firmware.

## Overview

This project provides utilities to work with Snapmaker U1 firmware images.
It enables creating custom firmware builds, and enabling debug features,
like SSH access.

## Features

- Extract firmware images (SquashFS rootfs)
- Create custom firmware with modifications
- Enable SSH: `root/snapmaker` and `lava/snapmaker`
- Enable DHCP on USB ethernet adapters

## Pre-builts

1. Go to [Actions](https://github.com/paxx12/SnapmakerU1/actions/workflows/build.yaml). You need GitHub account.
1. Download latest artifact for latest build.
1. Unpack the `.zip`
1. Put the `.bin` file onto USB device (FAT32/exFAT format).
1. Go to `About > Firmware version > Local Update > Select firmware_custom.bin`
1. Connect using `ssh root@<ip>` with `snapmaker` password.

**This will void your warranty, but you get SSH access.**

Revert: flash stock firmware from [Snapmaker's site](https://wiki.snapmaker.com/en/snapmaker_u1/firmware/release_notes).

## License

See individual tool directories for licensing information.

## Disclaimer

This project is for educational and development purposes. Modifying firmware may void warranties and could potentially damage your device. Use at your own risk.
