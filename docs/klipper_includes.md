# Klipper and Moonraker Custom Includes

**Available in: Extended firmware**

The `enable-klipper-includes` overlay adds support for custom Klipper and Moonraker configuration files.

## What It Does

This overlay modifies the default Klipper and Moonraker configurations to include user-defined configuration files from specific directories:

- Klipper includes from: `extended/klipper/*.cfg`
- Moonraker includes from: `extended/moonraker/*.cfg`

## Usage

### Using Fluidd Web Interface

1. Open Fluidd in your web browser (`http://<printer-ip>`)
2. Go to **Configuration** tab
3. Navigate to the **klipper** folder to create Klipper configuration files (`.cfg`)
4. Navigate to the **moonraker** folder to create Moonraker configuration files (`.cfg`)
5. Create your custom configuration files using the interface
6. Restart the respective service after making changes

### Klipper Configuration

In the Fluidd Configuration tab, go to the **klipper** folder and create `.cfg` files with your custom Klipper configuration.

Example `custom-macros.cfg`:

```cfg
[gcode_macro CUSTOM_MACRO]
gcode:
    G28
    G1 Z10 F600
```

### Moonraker Configuration

In the Fluidd Configuration tab, go to the **moonraker** folder and create `.cfg` files with your custom Moonraker configuration.

Example `usb-camera.cfg` for USB camera support:

```conf
[webcam webcam2]
service: webrtc-camerastreamer
stream_url: /webcam2/webrtc
snapshot_url: /webcam2/snapshot.jpg
aspect_ratio: 16:9
```

## Important Notes

- All `.cfg` files in the `extended/klipper/` folder are automatically included
- All `.cfg` files in the `extended/moonraker/` folder are automatically included
- Configuration files persist across reboots
- Do not modify or remove the `00_keep.cfg` placeholder files
- Test changes carefully to avoid breaking the printer configuration
- Invalid configuration will prevent Klipper/Moonraker from starting

## Recovery from Extended Firmware Configuration Issues

If you break Moonraker with an invalid configuration, the printer will not connect to WiFi on next boot.

To recover:

1. Create an empty file named `extended-recover.txt` on a USB stick
2. Insert the USB stick into the printer
3. Restart the printer
4. The configuration folder will be backed up to `extended.bak`
5. The printer will start with a fresh configuration
6. Remove the USB stick and the `extended-recover.txt` file will be automatically deleted
