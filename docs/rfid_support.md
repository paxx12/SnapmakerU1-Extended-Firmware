---
title: RFID Filament Tag Support
---

# RFID Filament Tag Support

**Available in: All firmware (extended adds OpenSpool support)**

The Snapmaker U1 automatically detects filament properties by reading RFID tags on spools.

**Firmware Support:**
- **Original & Basic:** Mifare Classic 1K with Snapmaker proprietary format
- **Extended:** Adds NTAG215/216 support with OpenSpool format

## Supported Formats

| Feature | OpenSpool 🏆 | OpenPrintTag | OpenTag3D | Snapmaker |
|---------|--------------|--------------|-----------|-----------|
| **Tag Type** | NTAG215 (540 bytes) / NTAG216 (888 bytes) | ISO15693/SLIX2 | NTAG215/216 or ISO15693/SLIX2 | Mifare Classic 1K |
| **Encoding** | JSON (NDEF) | CBOR (NDEF) | Binary | Proprietary + RSA signature |
| **Data Format** | Human-readable JSON | Compact CBOR binary | Binary | Encrypted proprietary |
| **Specification** | [openspool.io](https://openspool.io/rfid.html) | [specs.openprinttag.org](https://specs.openprinttag.org/#/) | [OpenTag3D](https://github.com/prusa3d/OpenTag3D) | Proprietary (closed) |
| **GitHub Repository** | [spuder/OpenSpool](https://github.com/spuder/OpenSpool) | [prusa3d/OpenPrintTag](https://github.com/prusa3d/OpenPrintTag) | [queengooborg/OpenTag3D](https://github.com/queengooborg/OpenTag3D) | N/A |
| **Popularity** | ⭐⭐⭐ (623 stars) | ⭐⭐ (213 stars) | ⭐ (17 stars) | N/A |
| **Programming Tools** | Any NDEF-capable NFC app | Prusa app only | [opentag3d.info/make](https://opentag3d.info/make) | Snapmaker official only |
| **U1 Compatible** | ✅ Yes (extended firmware) | ❌ No (ISO15693 not supported) | ⚠️ Not implemented yet | ✅ Yes (all firmware) |
| **Ease of Programming** | Easy (any NFC app) | Medium (requires Prusa app) | Medium (web-based tool) | Hard (official tags only) |
| **Data Portability** | High (simple JSON) | High (open CBOR spec) | Medium (binary format) | None (proprietary) |

🏆 = Recommended for U1 (NTAG215 is the sweet spot for capacity and compatibility)

## How It Works

Tags are automatically read when filament is loaded into the feeder. Tag data clears when filament is removed.

**Manual Commands:**
- Read tag: `FILAMENT_DT_UPDATE CHANNEL=<n>`
- Clear tag data: `FILAMENT_DT_CLEAR CHANNEL=<n>`
- Check current tag: `FILAMENT_DT_QUERY CHANNEL=<n>`

## Programming Filament Tags

### OpenSpool (Recommended for Extended Firmware)

**Quick Setup:**
1. Get NTAG215 or NTAG216 tags
2. Open Chrome on Android phone
3. Visit [printtag-web.pages.dev](https://printtag-web.pages.dev)
4. Enter filament information
5. Tap tag to phone to write

**Alternative:** Use any NFC app that supports NDEF with JSON (MIME type: `application/json`)

Example payload:
```json
{
  "protocol": "openspool",
  "version": "1.0",
  "brand": "Generic",
  "type": "PLA",
  "color_hex": "#FF0000",
  "min_temp": 190,
  "max_temp": 220,
  "bed_min_temp": 50,
  "bed_max_temp": 60
}
```

Using the non-standard OpenSpool `subtype` field it is possible to specify a material subtype:

```json
{
  "protocol": "openspool",
  "version": "1.0",
  "type": "PETG",
  "subtype": "Rapid",
  "color_hex": "AFAFAF",
  "additional_color_hexes": ["EEFFEE","FF00FF"],
  "alpha": "FF",
  "brand": "Elegoo",
  "min_temp": "230",
  "max_temp": "260"
}
```

### OpenSpool Field Reference

**Required Fields:**
- `protocol` - Must be "openspool"
- `version` - Specification version (e.g., "1.0")
- `type` - Material type (PLA, PETG, ABS, TPU, etc.)
- `color_hex` - Color in hex format (#RRGGBB)

**Optional Standard Fields:**
- `brand` - Manufacturer name
- `min_temp` / `max_temp` - Nozzle temperature range in °C

**Optional Extended Fields (U1-specific):**
- `bed_min_temp` / `bed_max_temp` - Bed temperature range in °C
- `subtype` - Material variant (Basic, Rapid, HF, Silk, etc.)
- `alpha` - Color transparency (00-FF hex, default: FF)
- `additional_color_hexes` - Additional colors for multicolor spools (up to 4)
- `weight` - Spool weight in grams
- `diameter` - Filament diameter in mm (e.g., 1.75)

### Snapmaker Orca Naming Convention

Snapmaker Orca requires filaments to follow this naming pattern: `<brand> <type> <subtype>`

Examples: `Generic PLA Basic`, `Elegoo PETG Rapid`

## Reading Existing Tags

Use the **NFC Tools** app (iOS/Android) to inspect tags:

1. Download NFC Tools from App Store or Google Play
2. Tap "Read" and hold tag to phone
3. Check tag type and NDEF records

**Compatible tag types:** NTAG213/215/216, Mifare Classic 1K
**Note:** ISO15693 tags (OpenPrintTag) are not supported

## G-code Commands for Tag Management

The extended firmware includes commands to read, write, and update RFID tags directly from G-code.

### FILAMENT_TAG_WRITE - Write Raw NDEF Data to NTAG Tag

Write pre-encoded NDEF binary data to an NTAG tag. The NDEF payload is generated client-side (e.g., by the RFID Manager web UI library) and sent as URL-safe base64.

**Syntax:**
```gcode
FILAMENT_TAG_WRITE [CHANNEL=<0-3>] DATA=<base64>
```

**Parameters:**
- `CHANNEL` - Filament channel (0-3, default: 0)
- `DATA` - Complete NDEF message (CC + TLV + record + terminator) as URL-safe base64 encoded string

**Example:**
```gcode
FILAMENT_TAG_WRITE CHANNEL=0 DATA=4RBtAAMSElAQYXBwbGljYXRpb24vanNvbnsicHJvdG9jb2wiOiJvcGVuc3Bvb2wi...
```

**Safety:** Only works with NTAG tags. Will reject M1 (Snapmaker) tags to prevent corruption.

**Typical usage:** The RFID Manager web UI handles encoding automatically. This command is the low-level transport mechanism.

### FILAMENT_TAG_ERASE - Erase NTAG Tag

Erase all data from an NTAG tag to prepare it for reprogramming.

**Syntax:**
```gcode
FILAMENT_TAG_ERASE [CHANNEL=<0-3>] CONFIRM=1
```

**Parameters:**
- `CHANNEL` - Filament channel (0-3, default: 0)
- `CONFIRM` - Must be set to 1 to confirm erase operation (required)

**Example:**
```gcode
FILAMENT_TAG_ERASE CHANNEL=0 CONFIRM=1
```

**Safety:**
- Only works with NTAG tags (will reject M1 tags)
- Requires CONFIRM=1 parameter to prevent accidental erasure
- Writes empty NDEF structure, leaving tag ready for new data

## Web UI - RFID Tag Manager

The extended firmware includes a web-based RFID Tag Manager accessible at `/rfid/` (e.g., `http://yourprinter.local/rfid/`).

### Features

- **Visual tag status** - See all 4 extruders at a glance
- **Create tags** - Write new NTAG tags with OpenSpool format
- **Update tags** - Modify existing NTAG tag data
- **Export tags** - Export existing tag data in json format
- **Import tags** - Import json tag data to selected extruder
- **Erase tags** - Clear NTAG tags for reprogramming (not needed if updating a tag)
- **Real-time updates** - Automatic status refresh via Moonraker websocket
- **Color picker** - Visual color selection with transparency support
- **Multicolor support** - Add up to 5 colors for rainbow/multicolor filament

### Architecture

The web UI encodes NDEF data client-side using the [PrintTag-Web](https://github.com/paxx12/PrintTag-Web) library, then sends the raw bytes to Klipper for writing:

```
Web UI (OpenSpool JSON → NDEF encode) → Moonraker Websocket → Klipper FILAMENT_TAG_WRITE → FM175XX RFID reader → NTAG tag
```

**Static file serving** - UI files served by nginx from `/home/lava/www/rfid-manager/` via `/rfid/` location alias.

### Supported Tags

- ✅ **NTAG215/216** - Full read/write support
- ❌ **Mifare Classic 1K** - Read-only (cannot write M1 tags)

## Troubleshooting

**Tag not detected:**
- Ensure tag is NTAG213/215/216 or Mifare Classic 1K
- Position tag within 1-3cm of reader antenna
- Ensure you place on tag on the side next to the U1 housing, which will depend on which side of the printer you load the spool
- If a vendor tag is present, for example Bambu Lab filament tags, this will usually interfere with reading a user-provided tag (you can cover up the vendor tag with foil tape)
- Manually read tag: `FILAMENT_DT_UPDATE CHANNEL=<n>` then `FILAMENT_DT_QUERY CHANNEL=<n>`
- Check `klippy.log` for detection messages

**OpenPrintTag tags don't work:**
- Expected - OpenPrintTag uses ISO15693 which is not supported by U1 hardware
- Use NTAG tags with OpenSpool format instead

**NTAG tags only work on extended firmware:**
- Basic and original firmware only support Mifare Classic 1K with Snapmaker proprietary format
- Extended firmware adds NTAG215/216 support
