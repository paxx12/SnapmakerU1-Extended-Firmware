---
title: VPN Remote Access (Experimental)
---

# VPN Remote Access (Experimental)

**Available in: Extended firmware only**

Control your printer remotely using a VPN provider.

> **Warning**: This feature is experimental. VPN services consume additional CPU and memory resources which may affect print quality or reliability during active prints. It is recommended to disable VPN while printing or monitor system performance closely.

## Supported Providers

- **tailscale** - Access your printer on your [Tailnet](https://tailscale.com)

## Enabling VPN

VPN is **disabled by default**.

### Using firmware-config Web UI

Navigate to the firmware-config interface and select Tailscale under VPN Provider. This will automatically download and install Tailscale.

### Manual Setup

**Step 1:** Download Tailscale (requires internet connection):
```bash
ssh root@<printer-ip>
tailscale-pkg download
```

**Step 2:** Edit `extended/extended.cfg`, set the `provider`:
```ini
[vpn]
provider: tailscale
```

**Step 3:** Start the VPN service:
```bash
/etc/init.d/S99vpn restart
```

## Tailscale Setup

Tailscale setup requires [SSH access](ssh_access.md) to the printer.

**Login to your tailnet:**

Use the [tailscale CLI up command](https://tailscale.com/kb/1241/tailscale-up) to login. Get a login link, QR code, or use an auth token to complete the login.

```bash
tailscale up

# show your tailscale IP
tailscale status | grep lava
100.95.6.132     lava               username@  linux    -
```

Note: You can use `tailscale up --ssh` to enable [tailscale SSH](https://tailscale.com/kb/1193/tailscale-ssh) and bypass passwords and keys.

### Features

- Gain full access to your printer from anywhere
- Requires no port forwarding
- Tailscale runs in [Userspace Mode](https://tailscale.com/kb/1177/kernel-vs-userspace-routers#userspace-netstack-mode), there is no access to TUN

### Tailscale Certificates

Tailscale can help generate Let's Encrypt SSL certificates for your printer, using [Tailscale Serve](https://tailscale.com/kb/1312/serve)! This will securly terminate SSL and forward requests to Fluidd/Mainsail.

```
tailscale serve --bg 80
tailscale serve reset # to disable
```

You can now browse securly to:
https://lava.${YOUR_TAILNET}.ts.net/

Note: The first time you load this it will take a minute to generate the certificate for the first time.
Note: Advanced users can enable [Funnel](https://tailscale.com/kb/1223/funnel) to expose Fluidd/Mainsail to the public internet. Only do this if you absutely know what you are doing to stay secure. Stay safe!
