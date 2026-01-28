---
title: Firmware Configuration
---

# Firmware Configuration

**Available in: Extended firmware**

The extended firmware provides two ways to configure firmware behavior:

1. **Firmware Config Web Interface** - A web-based tool for managing settings, firmware upgrades, and troubleshooting
2. **extended.cfg** - A configuration file for customizing firmware behavior

## Firmware Config Web Interface

Access the Firmware Config tool at `http://<printer-ip>/firmware-config/`

**Note:** The Firmware Config interface is only available when Advanced Mode is enabled. On the printer touchscreen, go to **Settings > Maintenance > Advanced Mode** and enable it, then restart the printer.

### Status

Displays system information including:
- Base firmware version
- Build version and profile
- Active firmware slot (A/B)
- Device name

### Quick Links

Dynamic links based on current settings:
- **Web Interface** - Opens Fluidd/Mainsail
- **Internal Camera** - Camera stream (when paxx12 stack is enabled)
- **USB Camera** - USB camera stream (when enabled)
- **Remote Screen** - Remote screen access (when enabled)

### Settings

Toggle settings directly from the web interface:

| Setting | Options | Description |
|---------|---------|-------------|
| Web Frontend | Fluidd, Mainsail | Switch between web interfaces |
| Camera Stack | Paxx12, Snapmaker | Select camera service |
| Camera RTSP Stream | Enabled, Disabled | Enable RTSP streaming |
| USB Camera | Enabled, Disabled | Enable USB camera support |
| Remote Screen | Enabled, Disabled | Enable remote screen access |
| Klipper Metrics Exporter | Enabled, Disabled | Enable Prometheus metrics |
| VPN Provider | None, Tailscale | Enable VPN remote access (Experimental) |

Changes are applied immediately and relevant services are restarted.

### Troubleshooting

Available actions:
- **Show MCUs Version** - Display microcontroller firmware versions
- **Collect System Logs** - Generate and download system logs for debugging
- **Restart Klipper** - Restart the Klipper service
- **Restart Moonraker** - Restart the Moonraker service
- **Reboot System** - Reboot the printer
- **Revert Changes** - Remove configuration changes and disable data persistence
- **Recover to Backup Firmware** - Restore previous firmware version

### Firmware Upgrade

Upgrade firmware using one of two methods:

**Download from URL:**
1. Enter a firmware URL
2. Click "Download & Upgrade"
3. The system downloads and installs the firmware

**Upload File:**
1. Select or drag-and-drop a firmware file
2. Click "Upload & Upgrade"
3. The file is uploaded and installed

The system reboots automatically after a successful upgrade.

## Configuration File (extended.cfg)

For advanced configuration, edit the configuration file directly.

### File Location

```
/home/lava/printer_data/config/extended/extended.cfg
```

### Editing the Configuration File

The `extended.cfg` file is automatically created by the firmware.

#### Via Fluidd/Mainsail

1. On the printer, go to **Settings > Maintenance > Advanced Mode** and enable it
2. Open Fluidd or Mainsail in your web browser (`http://<printer-ip>`)
3. Go to the **Configuration** tab
4. Navigate to the `extended` directory and open `extended.cfg`
5. Add or modify your configuration options (see below)
6. Save the file
7. Reboot the printer

#### Via SSH

```bash
ssh lava@<printer-ip>
vi /home/lava/printer_data/config/extended/extended.cfg
```

After saving, reboot the printer.

### Configuration Options

#### [firmware_config]

**enabled** - Enable or disable the Firmware Config web interface
- `true` (default) - Firmware Config available at `/firmware-config/` when Advanced Mode is enabled
- `false` - Firmware Config disabled even when Advanced Mode is enabled

#### [vpn]

**provider** - VPN provider for remote access (only one can be active)
- `none` (default) - VPN disabled
- `tailscale` - Connect to your Tailnet via [Tailscale](https://tailscale.com)

See [VPN Remote Access](vpn.md) for setup instructions.

#### [camera]

**stack** - Camera stack selection (only one can be active)
- `paxx12` (default) - Hardware-accelerated v4l2-mpp camera stack with WebRTC and timelapse
- `snapmaker` - Native Snapmaker camera service

**logs** - Camera service logging destination
- `syslog` - Enable logging to `/var/log/messages`

**rtsp** - Enable RTSP streaming support (paxx12 stack only)
- `true` - Enable RTSP streaming at `rtsp://<printer-ip>:8554/stream` (internal) and `rtsp://<printer-ip>:8555/stream` (USB)
- `false` (default) - RTSP streaming disabled

**usb** - Enable USB camera support (paxx12 stack only)
- `true` - Enable USB camera streaming at `http://<printer-ip>/webcam2/`
- `false` (default) - USB camera disabled

#### [web]

**frontend** - Web interface selection (only one can be active)
- `fluidd` (default) - Fluidd web interface
- `mainsail` - Mainsail web interface

#### [remote_screen]

**enabled** - Enable remote screen access at `http://<printer-ip>/screen/`
- `true` - Enable remote screen viewing and touch control in web browser
- `false` (default) - Remote screen access disabled

Note: Requires additional Moonraker configuration. See [Remote Screen Access](remote_screen.md) for complete setup.

#### [monitoring]

**klipper_exporter_enabled** - Enable Prometheus metrics exporter for Klipper
- `true` - Enable metrics at `http://<printer-ip>:9101/metrics`
- `false` (default) - Klipper exporter disabled

**klipper_exporter_address** - Metrics exporter listen address
- `:9101` (default) - Listen on all interfaces, port 9101
- Custom format: `[host]:port` (e.g., `127.0.0.1:9101`, `:8080`)

See [Monitoring](monitoring.md) for integration with Grafana, Home Assistant, or DataDog.

### Example Configuration

```ini
[firmware_config]
# enabled: true
# enabled: false

[camera]
stack: paxx12
# stack: snapmaker
logs: syslog
# rtsp: true
# usb: true

[web]
frontend: fluidd
# frontend: mainsail

[remote_screen]
# enabled: true

[monitoring]
# klipper_exporter_enabled: true
# klipper_exporter_address: :9101

[vpn]
# provider: tailscale
```

### Identifying Customized Settings

When you modify a configuration file, the system automatically creates a `.default` file alongside it containing the original default values. For example, if you customize `extended.cfg`, you'll find `extended.cfg.default` in the same directory.

This makes it easy to:
- See which files you have customized
- Compare your changes against the defaults
- Restore default values if needed

The `.default` files are updated on each boot to reflect the current firmware defaults.

## Important Notes

- After making changes to `extended.cfg`, reboot the printer for changes to take effect
- The file uses INI-style format with sections like `[camera]` and `[web]`
- Lines starting with `#` are comments and ignored
- Only one camera stack can be active at a time
- Only one web interface can be active at a time
- Changes made via the Firmware Config web interface are written to `extended.cfg`

## Recovery & Reset

### Reset to Default Configuration

To restore default extended configuration, remove or rename the `extended` folder in Fluidd/Mainsail Configuration tab, then reboot.

### Recovery from Configuration Issues

If an invalid configuration breaks Moonraker (printer won't connect to WiFi):

1. Create an empty file named `extended-recover.txt` on a USB drive
2. Insert the USB drive into the printer
3. Restart the printer
4. The extended configuration will be backed up to `extended.bak` and reset to defaults
5. Remove the USB drive (the recovery file will be automatically deleted)

## Related Documentation

- [Camera Support](camera_support.md) - Camera features and WebRTC streaming
- [Klipper and Moonraker Custom Includes](klipper_includes.md) - Add custom configuration files
- [Data Persistence](data_persistence.md) - Understanding persistent storage
- [VPN Remote Access](vpn.md) - Secure remote access via Tailscale
