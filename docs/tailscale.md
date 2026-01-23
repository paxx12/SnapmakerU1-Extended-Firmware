---
title: Tailscale Remote Access
---

# Tailscale Remote Access

**Available in: Extended firmware only**

Control your printer remotely on your Tailnet using [Tailscale](https://tailscale.com).

## Features

- Gain full access to your printer from anywhere
- Requires no port forwarding
- Tailscale runs in [Userspace Mode](https://tailscale.com/kb/1177/kernel-vs-userspace-routers#userspace-netstack-mode), there is not access to TUN


## Enabling Tailscale

Tailscale is **disabled by default**. To enable:

**Step 1:** Edit `extended/extended.cfg`, locate the `enabled` setting and set it to `true`:
```ini
[tailscale]
enabled: true
```

**Editing via SSH:**
```bash
ssh root@<printer-ip>
vi /home/lava/printer_data/config/extended/extended.cfg
```

**Step 2:** Reboot the printer 

Or run `/etc/init.d/S22-tailscale restart` to start the daemon.

**Step 3:** Login to your tailnet

Use the [tailscale CLI up command](https://tailscale.com/kb/1241/tailscale-up) to login. Get a login link, QR code, or use an auth token to complete the login.  

```bash
tailscale up

# show your tailscale IP
tailscale status | grep lava
100.95.6.132     lava               username@  linux    -
```

Note: You can use `tailscale up --ssh` to enable [tailscale SSH](https://tailscale.com/kb/1193/tailscale-ssh) and bypass passwords and keys.


## Tailscale Certificates

Tailscale can help generate Let's Encrypt SSL certificates for your printer, using [Tailscale Serve](https://tailscale.com/kb/1312/serve)! This will securly terminate SSL and forward requests to Fluidd/Mainsail.

```
tailscale serve --bg 80
tailscale serve reset # to disable
```

You can now browse securly to:
https://lava.${YOUR_TAILNET}.ts.net/

Note: The first time you load this it will take a minute to generate the certificate for the first time. 
Note: Advanced users can enable [Funnel](https://tailscale.com/kb/1223/funnel) to expose Fluidd/Mainsail to the public internet. Only do this if you absutely know what you are doing to stay secure. Stay safe!
