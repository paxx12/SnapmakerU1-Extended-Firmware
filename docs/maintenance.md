---
title: Maintenance Tool
---

# Maintenance Tool

**Available in: Basic and Extended firmware**

The Maintenance Tool provides a web-based interface for system administration and troubleshooting without requiring SSH access.

## Accessing the Tool

Navigate to `http://<printer-ip>/maintenance/` in your web browser.

## Features

### System Information

View current system status including:

- Firmware version and custom firmware version
- Current boot slot (A/B)
- Network configuration (IP addresses, MAC addresses)
- WiFi connection status and signal strength

### Firmware Upgrade

Upgrade firmware directly from the web interface:

- Upload firmware files from your computer
- Download and install firmware from a URL

### Quick Actions

Execute common maintenance tasks:

- View MCU versions and system status
- Collect system logs for troubleshooting
- Restart Klipper or Moonraker services
- Reboot the system
- Switch to backup firmware slot

### Settings

Configure system options (availability depends on firmware variant and installed features).

> **Warning**: Do not change settings during printing. Changing settings will restart relevant services which may interrupt an active print.
