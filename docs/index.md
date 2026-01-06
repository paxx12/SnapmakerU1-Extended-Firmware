# Custom Snapmaker U1 Firmware

Custom firmware for the Snapmaker U1 3D printer, enabling debug features like SSH access and adding additional capabilities.

> **Warning**: Installing custom firmware may void warranty and could potentially damage your device.
> Use at your own risk.

## Download

Get the latest pre-built firmware from [Releases](https://github.com/paxx12/SnapmakerU1/releases).

For installation instructions, see [Installation Guide](install.md)
and the [release notes](https://github.com/paxx12/SnapmakerU1/releases/latest).

## Features

### Basic Firmware

- [SSH Access](ssh_access.md) - Remote shell access with `root/snapmaker` and `lava/snapmaker`
- USB Ethernet Adapters - Hot-plug support with automatic DHCP configuration
- [Data Persistence](data_persistence.md) - Persistent storage across firmware updates
- Enable fluidd automatically with camera feed.

### Extended Firmware

All basic firmware features plus:

- [Extended Configuration](extended_config.md) - Customize firmware behavior via config file
- [Camera Support](camera_support.md) - Hardware-accelerated camera stack (Rockchip MPP/VPU)
- [USB Camera Support](camera_support.md) - Support for external USB cameras
- [Klipper and Moonraker Custom Includes](klipper_includes.md) - Add custom configuration files via Fluidd/Mainsail
- [RFID Filament Tag Support](rfid_support.md) - NTAG213/215/216 support for OpenPrintTag and OpenSpool formats
- Moonraker Adaptive Mesh Support - Object processing for adaptive mesh features
- Moonraker Apprise notifications - Send print notifications to Discord, Telegram, Slack, and 90+ services
- WebRTC low-latency streaming
- Fluidd or Mainsail (selectable) with timelapse plugin
- [Remote Screen](remote_screen.md) - View printer screen remotely via web browser
- [Monitoring](monitoring.md) - Local OpenMetrics exporter for monitoring systems

Known issues:

- The time-lapses are not available via mobile app when using Snapmaker Cloud.

## Documentation

- [Installation Guide](install.md) - How to install custom firmware
- [Building from Source](development.md) - Development guide for building custom firmware
- [SSH Access](ssh_access.md) - How to access the printer via SSH
- [Extended Configuration](extended_config.md) - Customize firmware behavior via config file
- [Camera Support](camera_support.md) - Camera features and WebRTC streaming
- [Klipper and Moonraker Custom Includes](klipper_includes.md) - Add custom configuration files
- [RFID Filament Tag Support](rfid_support.md) - RFID filament tag usage and programming
- [Data Persistence](data_persistence.md) - Persistent storage configuration
- [Remote Screen](remote_screen.md) - Access printer screen remotely via web browser
- [Monitoring](monitoring.md) - Prometheus, Homeassistant integration, Datadog, monitoring, etc.

## Support

If you find this project useful and would like to support its development, you can:

[![Buy Me A Coffee](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/paxx12)
