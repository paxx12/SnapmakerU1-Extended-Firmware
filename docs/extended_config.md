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
4. Navigate to the root directory and open `extended.cfg`
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

* `stack` - Camera stack selection (only one can be active)

  * `paxx12` - Hardware-accelerated v4l2-mpp camera stack (WebRTC, timelapse)
  * `snapmaker` - Native Snapmaker camera service

* `logs` - Camera service logging destination

  * `syslog` - Enable logging to syslog (/var/log/messages)

## Example Configuration

```ini
[camera]
stack: paxx12
# stack: snapmaker
logs: syslog
```

## Important Notes

- After making changes to `extended.cfg`, reboot the printer
- The file uses INI-style format with sections `[camera]` and `[web]`
- Lines starting with `#` are comments and ignored
- Only one camera stack can be active at a time

## Revert back to defaults

If you decide to go back to default extended configuration,
simply remove or rename `extended` folder in Fluidd/Mainsail.

## Recovery from Extended Configuration issue

If you break Moonraker with an invalid configuration, the printer will not connect to WiFi on next boot.

To recover:

1. Create an empty file named `extended-recover.txt` on a USB stick
2. Insert the USB stick into the printer
3. Restart the printer
4. The extended configuration folder will be backed up to `extended.bak`
5. The printer will start with a fresh configuration
6. Remove the USB stick and the `extended-recover.txt` file will be automatically deleted

## Related Documentation

- [Camera Support](camera_support.md) - Camera features and WebRTC streaming
- [Klipper and Moonraker Custom Includes](klipper_includes.md) - Add custom configuration files
- [Data Persistence](data_persistence.md) - Understanding persistent storage
