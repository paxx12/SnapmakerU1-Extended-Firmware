---
title: Cloud Remote Access (Experimental)
---

# Cloud Remote Access (Experimental)


Control your printer remotely using cloud-based remote access providers.

> **Note**: Cloud providers are downloaded on-demand when enabled by the user. See [third-party integration design](design/third_party.md) for details on how external components are managed.

> **Warning**: This feature is experimental. Cloud services consume additional CPU and memory resources which may affect print quality or reliability during active prints. It is recommended to monitor system performance closely.

## Supported Providers

- **none** - Cloud access disabled (default)
- **octoeverywhere** - Remote access via [OctoEverywhere.com](https://octoeverywhere.com)
- **cloudflared** - Remote access via [Cloudflare Tunnel](https://www.cloudflare.com/products/tunnel/)

## OctoEverywhere

- Access your printer remotely from anywhere
- AI print failure detection and notifications
- Webcam streaming and timelapse
- Requires no port forwarding or VPN configuration

### Using firmware-config Web UI (preferred)

Navigate to the [firmware-config](firmware_config.md) web interface, go to the Remote Access section, and select OctoEverywhere under Cloud Provider. This will automatically download and install the OctoEverywhere plugin and display the account linking instructions.

### Manual Setup (advanced)

**Step 1:** Download OctoEverywhere (requires internet connection):
```bash
ssh root@<printer-ip>
octoeverywhere-pkg download
```

**Step 2:** Edit `extended/extended2.cfg`, set the `cloud`:
```ini
[remote_access]
cloud: octoeverywhere
```

**Step 3:** Start the cloud service:
```bash
/etc/init.d/S99cloud restart
```

**Step 4:** Link your account by downloading `octoeverywhere.log` from Mainsail or Fluidd to find the account linking URL. Open the URL in your browser to link your printer to your OctoEverywhere.com account.

**Need help?** Visit [OctoEverywhere Support for Snapmaker U1](https://octoeverywhere.com/s/snapmaker-u1) for assistance.

## Cloudflared

- Secure remote access using Cloudflare Tunnel
- No port forwarding required
- Lower resource usage compared to OctoEverywhere
- Requires Cloudflare account setup

### Cloudflare Account Setup

1. **Create a Cloudflare Account**: Sign up at [https://cloudflare.com](https://cloudflare.com)

2. **Add Your Domain**: Add your domain to Cloudflare if you haven't already

3. **Create a Tunnel**:
   - Go to the Cloudflare dashboard
   - Navigate to **Access** → **Tunnels**
   - Click **Create a tunnel**
   - Choose **Cloudflared** as the connector
   - Give your tunnel a name (e.g., "snapmaker-u1")
   - Add a public hostname that points to your domain
   - Set the service to `http://localhost:80`

4. **Get Tunnel Token**: After creating the tunnel, Cloudflare will provide a tunnel token. Save this token as you'll need it for the firmware configuration.

### Firmware Configuration

Navigate to the [firmware-config](firmware_config.md) web interface, go to the Remote Access section, and select Cloudflared under Cloud Provider. This will download and enable Cloudflared on your printer and show you further instructions.

After enabling Cloudflared, you need to add your tunnel token to the configuration:

1. **Edit the configuration file** (via SSH or using a file editor):
```ini
/home/lava/printer_data/config/extended/extended2.cfg
```

2. **Add the tunnel token** under the `[remote_access]` section:
```ini
[remote_access]
cloud: cloudflared
cloudflared_token: YOUR_TUNNEL_TOKEN_HERE
```

3. **Restart the cloud service**:
```bash
/etc/init.d/S99cloud restart
```

The Cloudflared service will now start with your configured tunnel token.

### Manual Setup (advanced)

**Step 1:** Download Cloudflared (requires internet connection):
```bash
ssh root@<printer-ip>
cloudflared-pkg download
```

**Step 2:** Edit `extended/extended2.cfg` and add both the `cloud` setting and your tunnel token:
```ini
[remote_access]
cloud: cloudflared
cloudflared_token: YOUR_TUNNEL_TOKEN_HERE
```

**Step 3:** Start the cloud service:
```bash
/etc/init.d/S99cloud restart
```

### Configuration Files

- Tunnel token stored in `/home/lava/printer_data/config/extended/extended2.cfg`
- Service logs: `/home/lava/printer_data/logs/cloudflared.log`

### Troubleshooting

- Check logs: `tail -f /home/lava/printer_data/logs/cloudflared.log`
- Verify your tunnel is active in the Cloudflare dashboard
- Ensure your domain's DNS is properly configured in Cloudflare
