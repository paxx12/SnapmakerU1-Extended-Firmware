---
title: SSH Access
---

# SSH Access

**Available in: Basic and Extended firmware**

The custom firmware enables SSH access to the Snapmaker U1 printer.

## Configuration (Extended Firmware)

In Extended firmware, SSH is disabled by default.

### Using firmware-config Web UI (preferred)

Navigate to the [firmware-config](firmware_config.md) web interface, go to the Remote Access section, and enable SSH Access.

### Manual Setup (advanced)

**Step 1:** Edit `/home/lava/printer_data/config/extended/extended2.cfg` to enable SSH:
```ini
[remote_access]
ssh: true
```

**Step 2:** Reboot the printer for changes to take effect.

## Credentials

- User: `root` / Password: `snapmaker`
- User: `lava` / Password: `snapmaker`

## Connecting

```bash
ssh root@<printer-ip>
```

Replace `<printer-ip>` with your printer's IP address.

## Changing Passwords

To persist password changes across reboots, enable data persistence. See [Data Persistence](data_persistence.md).

## Security Considerations

- SSH provides full system access to your printer
- Only enable SSH on trusted networks
- Consider disabling SSH when not actively needed
- Change default credentials after first login
