---
title: Extended Configuration
---

# Extended Configuration

**Available in: Extended firmware**

The extended configuration file `/home/lava/printer_data/config/extended/extended.cfg` allows you to customize firmware behavior.

## Configuration File Location

```
/home/lava/printer_data/config/extended/extended.cfg
```

## Editing the Configuration File

The `extended.cfg` file is automatically created by the firmware.

### Via Fluidd/Mainsail

1. On the printer, go to **Settings > Maintenance > Advanced Mode** and enable it
2. Open Fluidd or Mainsail in your web browser (`http://<printer-ip>`)
3. Go to the **Configuration** tab
4. Navigate to the `extended` directory and open `extended.cfg`
5. Add or modify your configuration options (see below)
6. Save the file
7. Reboot the printer

### Via SSH

```bash
ssh lava@<printer-ip>
vi /home/lava/printer_data/config/extended/extended.cfg
```

After saving, reboot the printer.

## Configuration Options

### [camera]

**stack** - Camera stack selection (only one can be active)
- `paxx12` (default) - Hardware-accelerated v4l2-mpp camera stack with WebRTC and timelapse
- `snapmaker` - Native Snapmaker camera service

**logs** - Camera service logging destination
- `syslog` - Enable logging to `/var/log/messages`

**rtsp** - Enable RTSP streaming support (paxx12 stack only)
- `true` - Enable RTSP streaming at `rtsp://<printer-ip>:8554/stream` (internal) and `rtsp://<printer-ip>:8555/stream` (USB)
- `false` (default) - RTSP streaming disabled

### [web]

**frontend** - Web interface selection (only one can be active)
- `fluidd` (default) - Fluidd web interface
- `mainsail` - Mainsail web interface

### [remote_screen]

**enabled** - Enable remote screen access at `http://<printer-ip>/screen/`
- `true` - Enable remote screen viewing and touch control in web browser
- `false` (default) - Remote screen access disabled

Note: Requires additional Moonraker configuration. See [Remote Screen Access](remote_screen.md) for complete setup.

### [monitoring]

**klipper_exporter_enabled** - Enable Prometheus metrics exporter for Klipper
- `true` - Enable metrics at `http://<printer-ip>:9101/metrics`
- `false` (default) - Klipper exporter disabled

**klipper_exporter_address** - Metrics exporter listen address
- `:9101` (default) - Listen on all interfaces, port 9101
- Custom format: `[host]:port` (e.g., `127.0.0.1:9101`, `:8080`)

See [Monitoring](monitoring.md) for integration with Grafana, Home Assistant, or DataDog.

## Example Configuration

```ini
[camera]
stack: paxx12
# stack: snapmaker
logs: syslog
# rtsp: true

[web]
frontend: fluidd
# frontend: mainsail

[remote_screen]
# enabled: true

[monitoring]
# klipper_exporter_enabled: true
# klipper_exporter_address: :9101
```

## Identifying Customized Settings

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
