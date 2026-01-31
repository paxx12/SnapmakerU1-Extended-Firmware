---
title: USB Recovery
---

# USB Recovery

**Available in: Extended firmware**

The extended firmware supports USB-based recovery options that run early in the boot process. These allow you to recover from configuration issues, reset settings, or upgrade firmware without network access.

## How It Works

1. Create a trigger file on a USB drive (FAT32 formatted)
2. Insert the USB drive into the printer
3. Power on or reboot the printer
4. The trigger file is renamed and the action displays on screen with a 10-second countdown
5. The recovery action executes

The trigger file is renamed immediately when detected (before the countdown begins) to prevent repeated triggering if the action fails or the printer reboots unexpectedly.

## Recovery Options

### Reset Extended Configuration

**Trigger file:** `extended-recover.txt` (empty file)

Resets the extended firmware configuration to defaults:
- Backs up the current `extended` config directory to `extended.backup.N`
- Disables debug/data persistence mode

Use this when:
- Invalid configuration prevents the printer from connecting to WiFi
- Moonraker fails to start due to configuration errors
- You cannot login or forgot the password
- You want to start fresh with default settings

**Steps:**
1. Create an empty file named `extended-recover.txt` on a USB drive
2. Insert the USB drive and reboot the printer
3. Wait for the 10-second countdown and completion message
4. Remove the USB drive

Your previous configuration is preserved in the backup directory and can be restored manually if needed.

### Apply WiFi Configuration

**Trigger file:** `wpa_supplicant.txt`

Applies WiFi settings from a configuration file:
- Copies the file to the printer's WiFi configuration
- Only works if the printer GUI has been started at least once

Use this when:
- You need to configure WiFi without screen access
- Setting up a printer with a known network configuration

**Steps:**
1. Create a `wpa_supplicant.txt` file on a USB drive with your WiFi settings:
   ```
   ctrl_interface=/var/run/wpa_supplicant
   update_config=1
   country=US

   network={
       ssid="YourNetworkName"
       psk="YourPassword"
   }
   ```
2. Insert the USB drive and reboot the printer
3. Wait for the 10-second countdown and completion message
4. Remove the USB drive

### Firmware Upgrade

**Trigger file:** `i_want_to_upgrade_my_u1.bin` (firmware file)

Upgrades the printer firmware from a USB drive:
- Installs the firmware file
- Logs output to `i_want_to_upgrade_my_u1.log` on the USB drive
- Renames the file to `i_want_to_upgrade_my_u1-done.bin` after completion

Use this when:
- The current firmware does not start
- Network-based upgrade is not available
- You need to install a specific firmware version

**Steps:**
1. Download the firmware file and rename it to `i_want_to_upgrade_my_u1.bin`
2. Copy it to a USB drive
3. Insert the USB drive and reboot the printer
4. Wait for the upgrade to complete (this takes several minutes)
5. The printer will restart automatically

## Safety Features

- **Immediate trigger removal** - Trigger files are deleted as soon as detected, preventing repeated execution on reboot
- **10-second countdown** - Visual warning before action begins
- **Screen feedback** - Status displayed on the printer screen throughout

## Troubleshooting

### Recovery not triggering
- Ensure the USB drive is FAT32 formatted
- Check the trigger filename is exact (case-sensitive on some systems)
- Try a different USB drive
- Ensure the USB drive is inserted before powering on

### Screen shows nothing
- Recovery runs early in boot, before the normal UI starts
- If the screen stays black, the recovery may not have triggered
- Check that the printer detects the USB drive

## Related Documentation

- [Firmware Configuration](firmware_config.md) - Configuration options and web interface
- [Data Persistence](data_persistence.md) - Understanding debug mode and persistent storage
