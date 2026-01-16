---
title: SSH Access
---

# SSH Access

**Available in: Basic and Extended firmware**

The custom firmware enables SSH access to the Snapmaker U1 printer.

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
