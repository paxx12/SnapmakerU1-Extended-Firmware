# Snapmaker U1 Firmware Tools

Tools for extracting, modifying, and rebuilding Snapmaker U1 firmware.

## Overview

This project provides utilities to work with Snapmaker U1 firmware images.
It enables creating custom firmware builds, and enabling debug features,
like SSH access.

## Firmware Variants

| Variant | Description |
|---------|-------------|
| **Basic** | SSH, USB ethernet, native camera (~1Hz in Fluidd) |
| **Extended** | Basic + new camera stack with HW-accelerated streams |

### Common Features

- Enable SSH: `root/snapmaker` and `lava/snapmaker`
- Enable DHCP on USB ethernet adapters
- Disable WiFi power saving

### Extended Camera

The extended firmware replaces the native camera with a hardware-accelerated
stack using the Rockchip MPP/VPU.

Camera endpoints available at `http://<ip>/webcam/`:

| Endpoint | Description |
|----------|-------------|
| `/webcam/snapshot.jpg` | JPEG snapshot |
| `/webcam/stream.mjpg` | MJPEG stream (~15fps) |
| `/webcam/stream.h264` | H264 stream (raw) |
| `/webcam/player` | H264 web player |

Fluidd automatically picks up the webcam configuration.

## Pre-builts

1. Go to [Actions](https://github.com/paxx12/SnapmakerU1/actions/workflows/build.yaml). You need GitHub account.
1. Download `basic-build` or `extended-build` artifact.
1. Unpack the `.zip`
1. Put the `.bin` file onto USB device (FAT32/exFAT format).
1. Go to `About > Firmware version > Local Update > Select the .bin file`
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
