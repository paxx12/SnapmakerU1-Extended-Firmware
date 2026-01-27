---
title: SSH Access
---

# SSH Access

**Available in: Basic and Extended firmware**

The custom firmware enables SSH access to the Snapmaker U1 printer.

## Configuration (Extended Firmware)

In Extended firmware, SSH is **disabled by default** and can be enabled via the firmware-config web UI or by editing `extended.cfg`:

```ini
[ssh]
enabled: true
```

Changes take effect after restarting the SSH service or rebooting the printer.

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
