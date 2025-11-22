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
- Disable WiFi power saving
- Expose camera feed in Fluidd (~1Hz)

## Pre-builts

1. Go to [Actions](https://github.com/paxx12/SnapmakerU1/actions/workflows/build.yaml). You need GitHub account.
1. Download latest artifact for latest build.
1. Unpack the `.zip`
1. Put the `.bin` file onto USB device (FAT32/exFAT format).
1. Go to `About > Firmware version > Local Update > Select firmware_custom.bin`
1. Connect using `ssh root@<ip>` with `snapmaker` password.

**This will void your warranty, but you get SSH access.**

Revert: flash stock firmware from [Snapmaker's site](https://wiki.snapmaker.com/en/snapmaker_u1/firmware/release_notes).

## Persistence of data

By default the Snapmaker firmware wipes all user changes on every reboot.
This makes it bulletproof.

If for some reason you want to persist system-level changes to `/etc` (e.g., SSH passwords
or authorized keys), create the file with `touch /oem/.debug`.
Remove it with `rm /oem/.debug` and reboot to restore a pristine system.

The `/home/lava/printer_data` directory persists with and without `/oem/.debug`.

## License

See individual tool directories for licensing information.

## Disclaimer

This project is for educational and development purposes. Modifying firmware may void warranties and could potentially damage your device. Use at your own risk.
