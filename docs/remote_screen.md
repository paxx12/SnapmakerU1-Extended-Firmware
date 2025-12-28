# Remote Screen Access

**Available in: Extended firmware only**

The extended firmware includes web-based remote screen access with touch control, allowing you to interact with your printer's touchscreen from any device with a web browser.

## Features

- Full screen mirroring of the printer's display
- Touch input support (tap, swipe, multi-touch)
- Access from any device (desktop, tablet, phone)
- Authentication inherited from Fluidd/Mainsail web interface

## Accessing the Remote Screen

Once enabled, access the remote screen at:

```text
http://<printer-ip>/screen/
```

Replace `<printer-ip>` with your printer's IP address.

## Enabling Remote Screen Access

Remote screen access is **disabled by default**. To enable it:

### Via Fluidd/Mainsail

1. On the printer, go to **Settings > Maintenance > Advanced Mode** and enable it
2. Open Fluidd or Mainsail in your web browser (`http://<printer-ip>`)
3. Go to the **Configuration** tab
4. Navigate to the root directory and open `extended.cfg`
5. Add or modify the `[remote_screen]` section:

   ```ini
   [remote_screen]
   enabled: true
   ```

6. Save the file
7. Reboot the printer

### Via SSH

```bash
ssh lava@<printer-ip>
vi /home/lava/printer_data/config/extended/extended.cfg
```

Add or modify:

```ini
[remote_screen]
enabled: true
```

Save and reboot the printer.

## Security

- Reuses Fluidd/Mainsail authentication which is none by default
- Remote screen is disabled by default in [extended.cfg](../10-default-config/root/home/lava/default-config/extended/extended.cfg) because by default there is no authentication
- User has to explicitly enable it in `extended.cfg`
- Requires authentication only if Fluidd/Mainsail also require authentication (Moonraker config)

## Browser/Device Compatibility

The remote screen uses normal HTML and works with all modern browsers.
It can also be installed as a Progressive Web App (PWA) on supported devices for a more app-like experience.

## Troubleshooting

### Remote screen not accessible

1. Verify remote screen is enabled in `extended.cfg`
2. Reboot the printer after enabling
3. Check that you can access Fluidd/Mainsail web interfaces normally

### Screen appears frozen

1. Refresh the browser page
2. Check if the printer's physical screen is responding
3. Restart the remote screen service:

   ```bash
   ssh lava@<printer-ip>
   sudo /etc/init.d/S99fb-http restart
   ```

## Technical Details

The remote screen feature uses:

- **fb-http-server.py**: A lightweight Python HTTP server that serves the framebuffer as PNG snapshots and accepts touch input
- **nginx**: Serves the web interface and proxies WebSocket connections

For more technical information, see the [overlay README](../overlays/firmware-extended/99-remote-screen/README.md).
