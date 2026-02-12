---
title: Filament Detection
---

# Filament Detection

**Available in: Extended firmware only**

The extended firmware supports an alternative filament detection system that recognizes tagged spools from multiple manufacturers.

## Detection Systems

- **Official** - Snapmaker's official filament detection system (default)
- **Extended** - Custom filament detection system using the [filament-detect](https://github.com/suchmememanyskill/filament-detect) project, with support for multiple spool tagging formats

## Supported Spool Tagging Systems

The extended detection system supports the following spool tagging systems:

| System | Enabled by default | Remarks |
|--------|-------------------|--------------------------|
| Bambu | No | Requires `bambu_key` in configuration |
| Creality | No | Requires `creality_key` and `creality_encryption_key` in configuration |
| Anycubic | Yes | - |
| Snapmaker | Yes | - |
| [OpenSpool](https://openspool.io/) | Yes | - |
| TigerTag | Yes | Fully offline implementation |

## Configuration

### Using firmware-config Web UI (preferred)

Navigate to the [firmware-config](firmware_config.md) web interface, go to the Filament Detection section, and select the **Extended** detection system.

### Manual Setup (advanced)

**Step 1:** Edit `/home/lava/printer_data/config/extended/extended2.cfg` and set the detection system:
```ini
[filament_detection]
system: extended
```

**Step 2:** Reboot the printer for changes to take effect.

## Bambu Spool Configuration

Bambu tagged spools require an authentication key to read.

**Step 1:** Edit `/home/lava/printer_data/config/extended/extended2.cfg` and set the key:
```ini
[filament_detection]
bambu_key: <your 32 hex character key>
```

**Step 2:** Verify the key by logging into the machine via [SSH](ssh_access.md) and restarting the service:
```bash
/etc/init.d/S59filament-detect restart
```

## Creality Spool Configuration

Creality tagged spools require both an authentication key and an encryption key to read.

**Step 1:** Edit `/home/lava/printer_data/config/extended/extended2.cfg` and set both keys:
```ini
[filament_detection]
creality_key: <your 32 hex character key>
creality_encryption_key: <your 32 hex character key>
```

**Step 2:** Verify the keys by logging into the machine via [SSH](ssh_access.md) and restarting the service:
```bash
/etc/init.d/S59filament-detect restart
```
