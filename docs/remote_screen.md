---
title: Remote Screen Access
---

# Remote Screen Access

**Available in: Extended firmware only**

View and control your printer's touchscreen remotely from any web browser.

## Features

- Full screen mirroring with touch control support
- Works on desktop, tablet, and phone browsers
- Authentication inherited from Fluidd/Mainsail
- Progressive Web App (PWA) support

## Access

Once enabled: `http://<printer-ip>/screen/`

## Enabling Remote Screen

Remote screen is **disabled by default**. To enable:

**Step 1:** Edit `extended/extended.cfg`, locate the setting below and set it to true:
```ini
[remote_screen]
enabled: true
```

**Step 2:** Edit `extended/moonraker/04_remote_screen.cfg`, locate the setting below and set it to true:
```ini
[webcam gui]
enabled: true
```

**Step 3:** Reboot the printer

**Editing via Fluidd/Mainsail:**
1. Enable **Advanced Mode** in printer settings
2. Open Fluidd/Mainsail Configuration tab
3. Edit the configuration files
4. Save and reboot

**Editing via SSH:**
```bash
ssh lava@<printer-ip>
vi /home/lava/printer_data/config/extended/extended.cfg
vi /home/lava/printer_data/config/extended/moonraker/04_remote_screen.cfg
```

## Troubleshooting

**Remote screen not accessible:**
- Verify remote screen is enabled in both config files
- Reboot printer after enabling
- Check that Fluidd/Mainsail web interfaces work normally

**Screen appears frozen:**
- Refresh browser page
- Check if physical printer screen responds
- Restart service: `ssh lava@<printer-ip>` then `sudo /etc/init.d/S99fb-http restart`

## Technical Details

The remote screen uses a lightweight Python HTTP server (`fb-http-server.py`) that captures framebuffer snapshots and processes touch input, served through nginx. For implementation details, see [overlay README](../overlays/firmware-extended/99-remote-screen/README.md).
