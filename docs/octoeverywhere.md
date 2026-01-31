---
title: OctoEverywhere Remote Access
---

# OctoEverywhere

**Available in: Extended firmware only**

[OctoEverywhere.com](https://octoeverywhere.com) is a 3D printing community project that enables:

- Free & unlimited full Fluidd remote access.
- Free & unlimited AI print failure detection.
- Real-time print notifications to Email, SMS, Discord, etc.
- Remote access for iPhone & Android apps like Mobileraker and OctoApp.
- Multi-printer dashboard with quick access to snapshots, status, remote access, and print time completions.
- Live streaming, shared printer access, and more!


## Enabling OctoEverywhere

OctoEverywhere is **disabled by default**.

### Using firmware-config Web UI

Navigate to the firmware-config interface and select `enabled` under OctoEverywhere. This will automatically download and install the OctoEverywhere plugin.

> **After enabling OctoEverywhere, you must link your account! (see below)**

### Manual Setup

**Step 1:** Download OctoEverywhere (requires internet connection):
```bash
ssh root@<printer-ip>
octoeverywhere-pkg download
```

**Step 2:** Edit `extended/extended.cfg`, set the `octoeverywhere`:
```ini
[octoeverywhere]
enabled: true
```

**Step 3:** Start the OctoEverywhere plugin service:
```bash
/etc/init.d/S99octoeverywhere restart
```

## OctoEverywhere Account Linking

Once the OctoEverywhere plug-in is running, you need to link it with your OctoEverywhere.com account. Simply find account linking URL in the `octoeverywhere.log` file.

### Using Fluidd

- Open the Fluidd web interface
- Click the `{...}` Configuration icon on the side menu bar.
- In the `Other Files` section, under the `Logs` tab, find `octoeverywhere.log` and click to edit/open it.
- Look for account linking URL, it will be near the top.
- Open the URL in your browser, name your printer, and you're done!

### Using Mainsail

- Open the Mainsail web interface
- Click the `Machine` option in the side menu bar.
- In the `Config Files` section, set the `root` dropdown box to `logs`
- Find `octoeverywhere.log` file and click to open it.
- Look for account linking URL, it will be near the top.
- Open the URL in your browser, name your printer, and you're done!
