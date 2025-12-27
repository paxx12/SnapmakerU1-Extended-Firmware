# Remote Screen Access

**Available in: Extended firmware only**

The extended firmware includes web-based remote screen access with touch control, allowing you to interact with your printer's touchscreen from any device with a web browser.

## Features

- Full screen mirroring of the printer's display
- Touch input support (tap, swipe, multi-touch)
- Access from any device (desktop, tablet, phone)
- Secure localhost-only architecture (VNC server not exposed to network)
- No authentication yet! THIS IS A SECURITY RISK, we are working on integrating authentication with moonraker users.

## Accessing the Remote Screen

Once enabled, access the remote screen at:

```text
http://<printer-ip>/screen/
```

Or with auto-connect in case you want to monitor the screen in some other interface (Fluidd html webcam, Homeassistant, embed as iframe, etc):

```text
http://<printer-ip>/screen/vnc.html?autoconnect=true
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

## Configuration Options

### [remote_screen]

- `enabled` - Enable/disable remote screen access
  - `true` - Remote screen enabled
  - `false` - Remote screen disabled (default)

- `vnc_listen` - VNC server listen interface (advanced)
  - `127.0.0.1` - Listen on localhost only (default, recommended)
  - `0.0.0.0` - Listen on all interfaces (not recommended for security)

**Example configuration:**

```ini
[remote_screen]
enabled: true
vnc_listen: 127.0.0.1
```

## Security

The remote screen feature is designed with security in mind:

- VNC server binds to localhost only by default (not accessible from network)
- Access is only available through the nginx reverse proxy
- Uses Unix domain sockets for internal communication
- No separate authentication (inherits web interface access control)
  - CURRENTLY NOT IMPLEMENTED, THERE IS NO AUTHENTICATION

## Browser Compatibility

The remote screen uses HTML5 WebSocket and works with:

- Chrome/Chromium
- Firefox
- Safari
- Edge
- Mobile browsers (iOS Safari, Chrome Android)

## Troubleshooting

### Remote screen not accessible

1. Verify remote screen is enabled in `extended.cfg`
2. Reboot the printer after enabling
3. Check that you can access the web interface normally

### Screen appears frozen

1. Refresh the browser page
2. Check if the printer's physical screen is responding
3. Restart the remote screen service:

   ```bash
   ssh lava@<printer-ip>
   sudo /etc/init.d/S99websockify restart
   ```

## Technical Details

The remote screen feature uses:

- **framebuffer-vncserver**: Reads the display framebuffer and handles touch input
- **websockify**: Bridges WebSocket connections to VNC protocol
- **noVNC**: HTML5 VNC client in your browser
- **nginx**: Serves the web interface and proxies WebSocket connections

For more technical information, see the [overlay README](../overlays/firmware-extended/99-remote-screen/README.md).
