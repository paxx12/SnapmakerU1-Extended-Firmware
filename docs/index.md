---
title: Custom Snapmaker U1 Firmware
---

# Custom Snapmaker U1 Firmware

Custom firmware for the Snapmaker U1 3D printer, enabling debug features like SSH access and adding additional capabilities.

> **Warning**: While installing custom firmware does not automatically void the product warranty, any damage caused by or attributable to the installation or use of custom firmware is not covered under warranty. Use at your own risk. See [Snapmaker Terms of Use](https://www.snapmaker.com/terms-of-use) for details.
>
> Custom firmware is intended for users with appropriate technical knowledge. Ensure you understand the implications before proceeding.

## Getting Started

### Installation

Download the latest firmware from [Releases](https://github.com/paxx12/SnapmakerU1/releases).

**📖 [Installation Guide](install.md)** - Step-by-step installation instructions

[Release notes](https://github.com/paxx12/SnapmakerU1/releases/latest)

### Building from Source

For developers who want to build custom firmware, see [Building from Source](development.md).

## Community

Join the [Snapmaker Discord](https://discord.com/invite/snapmaker-official-1086575708903571536) and visit the **#u1-printer** channel to connect with other users using the custom firmware, share experiences, and get help.

## Firmware Variants

### Basic Firmware

Stock firmware with SSH access and minimal debugging features:

- [SSH Access](ssh_access.md) - Remote shell access with `root/snapmaker` and `lava/snapmaker`
- [Firmware Configuration](firmware_config.md) - Web-based system administration and firmware upgrades
- [Data Persistence](data_persistence.md) - Persistent storage configuration across firmware updates
- USB Ethernet Adapters - Hot-plug support with automatic DHCP configuration
- Fluidd web interface with basic camera support

### Extended Firmware

Heavily expanded firmware with extensive features and customization. Includes all basic features plus:

- [Firmware Configuration](firmware_config.md) - Customize firmware behavior via web interface or config file
- [USB Recovery](recovery.md) - Recovery options via USB drive for troubleshooting
- [Camera Support](camera_support.md) - Hardware-accelerated camera stack with WebRTC streaming for internal and USB cameras
- [Klipper and Moonraker Custom Includes](klipper_includes.md) - Add custom configuration files via Fluidd/Mainsail
- [RFID Filament Tag Support](rfid_support.md) - NTAG213/215/216 support for OpenSpool format
- [Remote Screen](remote_screen.md) - View and control printer screen remotely via web browser
- [Monitoring](monitoring.md) - Integration with Prometheus, Home Assistant, DataDog, and other monitoring systems
- [VPN Remote Access](vpn.md) - Secure remote access via Tailscale (Experimental)
- [Fluidd or Mainsail](firmware_config.md#web) (selectable) with timelapse support
- Moonraker Adaptive Mesh Support - Object processing for adaptive mesh features
- Moonraker Apprise Notifications - Send print notifications to Discord, Telegram, Slack, and 90+ services
- [Timelapse Recovery Tool](https://github.com/horzadome/snapmaker-u1-timelapse-recovery) - Recover unplayable timelapse videos

## Support

If you find this project useful and would like to support its development, you can:


[![Buy Me A Coffee](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/paxx12)

🖨️ **Buy a Snapmaker Printer from Official Store** - use referral link and discount code `PAXX12` to get 5% discount on any purchase

  * EU store: [https://snapmaker-eu.myshopify.com?ref=paxx12](https://snapmaker-eu.myshopify.com?ref=paxx12)
  * US store: [https://snapmaker-us.myshopify.com?ref=paxx12](https://snapmaker-us.myshopify.com?ref=paxx12)
  * Global store: [https://test-snapmaker.myshopify.com?ref=paxx12](https://test-snapmaker.myshopify.com?ref=paxx12)
