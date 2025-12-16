# Custom Snapmaker U1 Firmware

This project builds custom firmware for the Snapmaker U1 3D printer,
enabling debug features like SSH access and adding additional capabilities.

> **Warning**: Installing custom firmware may void warranty and could potentially damage your device.
> Use at your own risk.

## Download

Get the latest pre-built firmware from [Releases](https://github.com/paxx12/SnapmakerU1/releases).

For installation instructions, see [Installation Guide](docs/install.md)
and the [release notes](https://github.com/paxx12/SnapmakerU1/releases/latest).

## Features

### Basic Firmware

- [SSH Access](docs/ssh_access.md) - Remote shell access with `root/snapmaker` and `lava/snapmaker`
- USB Ethernet Adapters - Hot-plug support with automatic DHCP configuration
- [Data Persistence](docs/data_persistence.md) - Persistent storage across firmware updates
- Enable fluidd automatically with camera feed.

### Extended Firmware

All basic firmware features plus:

- [Camera Support](docs/camera_support.md) - Hardware-accelerated camera stack (Rockchip MPP/VPU)
- [USB Camera Support](docs/camera_support.md) - Support for external USB cameras
- [Klipper and Moonraker Custom Includes](docs/klipper_includes.md) - Add custom configuration files via Fluidd
- [RFID Filament Tag Support](docs/rfid_support.md) - NTAG213/215/216 support for OpenPrintTag and OpenSpool formats
- Moonraker Apprise notifications - Send print notifications to Discord, Telegram, Slack, and 90+ services
- WebRTC low-latency streaming
- Fluidd v1.35.0 with timelapse plugin

Known issues:

- The time-lapses are not available via mobile app when using Snapmaker Cloud.

## Documentation

- [Installation Guide](docs/install.md) - How to install custom firmware
- [Building from Source](docs/development.md) - Development guide for building custom firmware
- [SSH Access](docs/ssh_access.md) - How to access the printer via SSH
- [Camera Support](docs/camera_support.md) - Camera features and WebRTC streaming
- [Klipper and Moonraker Custom Includes](docs/klipper_includes.md) - Add custom configuration files via Fluidd
- [RFID Filament Tag Support](docs/rfid_support.md) - RFID filament tag usage and programming
- [Data Persistence](docs/data_persistence.md) - Persistent storage configuration

## Dependent projects

- [v4l2-mpp](https://github.com/paxx12/v4l2-mpp) - Custom project built to provide
  Hardware-accelerated camera stack

## Support

If you find this project useful and would like to support its development, you can:

[![Buy Me A Coffee](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/paxx12)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for information about contributing to this project.

## License

This project is free to use for personal usage. See [LICENSE](LICENSE) for details.

For licensing information about individual tools and dependencies, see their respective directories.
