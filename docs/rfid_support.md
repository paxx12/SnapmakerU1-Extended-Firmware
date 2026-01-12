---
title: RFID Filament Tag Support
---

# RFID Filament Tag Support

The Snapmaker U1 can automatically detect filament properties (material type, color, temperatures) by reading RFID tags attached to filament spools.

The extended firmware adds support for **NTAG tags** with OpenSpool format, while maintaining compatibility with original Snapmaker tags.

- **Original firmware:** Mifare Classic 1K with Snapmaker format only
- **Extended firmware:** Adds NTAG215/216 support (OpenSpool format)

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

### Tags Are Read When:

- Filament is loaded into the feeder
- Manually triggered via `FILAMENT_DT_UPDATE CHANNEL=<n>`
- On startup (if configured)

### Tag Data Clears When:

- Filament is removed from the feeder
- Manually cleared via `FILAMENT_DT_CLEAR CHANNEL=<n>`

## Programming Filament Tags

### OpenSpool (Recommended)

1. Get NTAG215 or NTAG216 tags
2. Open Chrome on your Android phone
3. Go to [printtag-web.pages.dev](https://printtag-web.pages.dev)
4. Enter filament information
5. Tap tag to phone to write

**Requirements:** Android phone with NFC + Chrome browser

Alternatively, use any NFC app that supports NDEF with JSON. Set MIME type to `application/json`.

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

**Supported OpenSpool Fields:**
- `protocol` (required) - Must be "openspool"
- `version` (required) - Specification version (e.g., "1.0")
- `type` (required) - Material type (e.g., "PLA", "PETG", "ABS")
- `color_hex` (required) - Color in hex format (e.g., "#FF0000")
- `brand` (optional) - Manufacturer name (e.g., "Generic", "Overture", "PolyLite")
- `min_temp` (optional) - Minimum nozzle temperature in °C
- `max_temp` (optional) - Maximum nozzle temperature in °C

**Supported non-standard OpenSpool Fields:**
- `bed_min_temp` (optional) - Minimum bed temperature in °C
- `bed_max_temp` (optional) - Maximum bed temperature in °C
- `subtype` (optional, default: "Basic") - Material subtype (e.g. "Rapid", "HF", "Silk")
- `alpha` (optional, default: "FF") - Alpha of color, range is (0x00..0xFF) (e.g., "00")
- `additional_color_hexes` (optional) - Additional colors, such as Silk Rainbow, up to 4 colors (e.g., ['EEFFEE', 'FF00FF'])
- `weight` (optional) - Spool weight in grams
- `diameter` (optional) - Filament diameter in mm (e.g. `1.75`)

## Snapmaker Orca Filament Naming Scheme

In order for Snapmaker Orca to recognize the filement, it must be named according to this naming scheme: `<brand> <type> <subtype>`, e.g. `Generic PLA Basic` and `Elegoo PETG Rapid`.

## Reading Existing Tags

To check what's on a tag before using it, use **NFC Tools** app (available on both iOS and Android):

1. Download **NFC Tools** from App Store (iOS) or Google Play (Android)
2. Open the app and tap "Read"
3. Hold your tag to the phone's NFC reader
4. The app will show:
   - **Tag type** (NTAG213/215/216, Mifare Classic, ISO15693, etc.)
   - **Memory size** and available space
   - **NDEF records** (for OpenPrintTag/OpenSpool tags)
   - **Raw data** stored on the tag

**What to look for:**
- **Tag Type:** Should be NTAG213/215/216 or Mifare Classic 1K
- **NDEF Message:** For OpenSpool, look for MIME type `application/json` with OpenSpool payload

If the tag shows ISO15693, it's an OpenPrintTag and won't work with Snapmaker U1.

## Common G-code Commands

```
# Check what tag detected
FILAMENT_DT_QUERY CHANNEL=0

# Force read tag
FILAMENT_DT_UPDATE CHANNEL=0

# Clear tag data
FILAMENT_DT_CLEAR CHANNEL=0
```

## Troubleshooting

**Tag not detected:**

- Ensure tag is NTAG213/215/216 or Mifare Classic 1K
- Position tag close to reader antenna (1-3cm)
- Try manual update: `FILAMENT_DT_UPDATE CHANNEL=<n>` and then `FILAMENT_DT_QUERY CHANNEL=<n>`
- Look in `klipper.log` to see if tags were discovered

**OpenPrintTag tags don't work:**

- Expected - OpenPrintTag uses ISO15693, Snapmaker uses ISO14443A
- Use NTAG with OpenSpool format instead

**NTAG tags don't work on original firmware:**

- NTAG support is only in extended firmware
- Original firmware only reads Mifare Classic 1K with Snapmaker proprietary format
