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

The extended firmware includes commands to read, write, and update RFID tags directly from G-code (available in version with tag writing support).

### FILAMENT_TAG_READ - Read Complete Tag Information

Display all information stored on an RFID tag.

**Syntax:**
```gcode
FILAMENT_TAG_READ [CHANNEL=<0-3>]
```

**Parameters:**
- `CHANNEL` - Filament channel (0-3, default: 0)

**Example:**
```gcode
FILAMENT_TAG_READ CHANNEL=0
```

**Output:**
```
=== RFID Tag Info - Channel 0 ===
Tag Type: NTAG (A)
UID: 04:12:34:56:78:90:00

Filament:
  Brand: Generic
  Type: PLA
  Diameter: 1.75 mm
  Density: 1.24 g/cm³
  Color: #FF0000

Temperature:
  Min Extruder: 190°C
  Max Extruder: 220°C
  Bed: 60°C
```

### FILAMENT_TAG_WRITE_OPENSPOOL - Write New NTAG Tag

Write complete OpenSpool format data to an NTAG tag. Use this to program blank tags or reprogram existing NTAG tags.

**Syntax:**
```gcode
FILAMENT_TAG_WRITE_OPENSPOOL [CHANNEL=<0-3>] TYPE=<material> [BRAND=<name>]
    [COLOR=<hex>] [ALPHA=<hex>] [COLOR2=<hex>] [COLOR3=<hex>] [COLOR4=<hex>] [COLOR5=<hex>]
    [DIAMETER=<mm>] [DENSITY=<g/cm³>] [MIN_TEMP=<°C>] [MAX_TEMP=<°C>]
    [BED_MIN_TEMP=<°C>] [BED_MAX_TEMP=<°C>] [BED_TEMP=<°C>]
    [WEIGHT=<grams>] [SUBTYPE=<text>]
```

**Required Parameters:**
- `TYPE` - Material type: PLA, PETG, ABS, TPU, PVA, NYLON, ASA, or PC

**Basic Parameters:**
- `CHANNEL` - Filament channel (0-3, default: 0)
- `BRAND` - Manufacturer name (default: "Generic")
- `COLOR` - Primary color as 6-digit hex code without # (default: FFFFFF)
- `DIAMETER` - Filament diameter in mm (default: 1.75)
- `DENSITY` - Material density in g/cm³ (uses material default if not specified)
- `SUBTYPE` - Material subtype, e.g., "Rapid", "Matte", "Silk" (optional)

**Temperature Parameters:**
- `MIN_TEMP` - Minimum hotend temperature in °C (optional)
- `MAX_TEMP` - Maximum hotend temperature in °C (optional)
- `BED_MIN_TEMP` - Minimum bed temperature in °C (optional)
- `BED_MAX_TEMP` - Maximum bed temperature in °C (optional)
- `BED_TEMP` - Legacy parameter for bed temperature (sets both min and max, optional)

**Extended Color Parameters:**
- `ALPHA` - Color transparency as 2-digit hex (00=transparent, FF=opaque, default: FF)
- `COLOR2` - Additional color 2 as 6-digit hex (for multicolor spools, optional)
- `COLOR3` - Additional color 3 as 6-digit hex (for multicolor spools, optional)
- `COLOR4` - Additional color 4 as 6-digit hex (for multicolor spools, optional)
- `COLOR5` - Additional color 5 as 6-digit hex (for multicolor spools, optional)

**Weight Tracking:**
- `WEIGHT` - Initial spool weight in grams (optional)

**Examples:**
```gcode
# Basic PLA tag
FILAMENT_TAG_WRITE_OPENSPOOL CHANNEL=0 TYPE=PLA BRAND="Generic" COLOR=FF0000 DIAMETER=1.75 MIN_TEMP=190 MAX_TEMP=220 BED_MIN_TEMP=50 BED_MAX_TEMP=70

# PETG tag with custom density and subtype
FILAMENT_TAG_WRITE_OPENSPOOL CHANNEL=0 TYPE=PETG BRAND="Elegoo" SUBTYPE="Rapid" COLOR=1E90FF DENSITY=1.27 MIN_TEMP=230 MAX_TEMP=260 BED_MIN_TEMP=70 BED_MAX_TEMP=90

# Transparent TPU with alpha transparency
FILAMENT_TAG_WRITE_OPENSPOOL CHANNEL=0 TYPE=TPU BRAND="Generic" COLOR=FFFFFF ALPHA=80 MIN_TEMP=210 MAX_TEMP=230 BED_MIN_TEMP=20 BED_MAX_TEMP=40

# Multicolor silk PLA (rainbow)
FILAMENT_TAG_WRITE_OPENSPOOL CHANNEL=0 TYPE=PLA BRAND="Generic" SUBTYPE="Silk" COLOR=FF0000 COLOR2=FF7F00 COLOR3=FFFF00 COLOR4=00FF00 COLOR5=0000FF MIN_TEMP=200 MAX_TEMP=220

# Tag with initial weight tracking (1kg spool)
FILAMENT_TAG_WRITE_OPENSPOOL CHANNEL=0 TYPE=PETG BRAND="Generic" COLOR=FF5500 WEIGHT=1000 MIN_TEMP=230 MAX_TEMP=250 BED_MIN_TEMP=70 BED_MAX_TEMP=85

# Using legacy BED_TEMP parameter (backward compatible)
FILAMENT_TAG_WRITE_OPENSPOOL CHANNEL=0 TYPE=PLA BRAND="Generic" COLOR=FFFFFF BED_TEMP=60
```

**Material Density Defaults:**
| Material | Density (g/cm³) |
|----------|-----------------|
| PLA      | 1.24            |
| PETG     | 1.27            |
| ABS      | 1.04            |
| TPU      | 1.21            |
| PVA      | 1.19            |
| NYLON    | 1.14            |
| ASA      | 1.07            |
| PC       | 1.20            |

**Safety:** Only works with NTAG tags. Will reject M1 (Snapmaker) tags to prevent corruption.

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

### Example Workflows

**Workflow 1: Program a Fresh NTAG Tag**
```gcode
# 1. Insert blank NTAG tag
# 2. Read to confirm it's NTAG
FILAMENT_TAG_READ CHANNEL=0

# 3. Write complete data
FILAMENT_TAG_WRITE_OPENSPOOL CHANNEL=0 TYPE=PLA BRAND="Polymaker" COLOR=FF5500 DIAMETER=1.75 MIN_TEMP=190 MAX_TEMP=220 BED_TEMP=60

# 4. Verify write
FILAMENT_TAG_READ CHANNEL=0
```

**Workflow 2: Reprogram an NTAG Tag**
```gcode
# 1. Erase existing data
FILAMENT_TAG_ERASE CHANNEL=0 CONFIRM=1

# 2. Write new data
FILAMENT_TAG_WRITE_OPENSPOOL CHANNEL=0 TYPE=PETG BRAND="Generic" COLOR=0000FF DIAMETER=1.75 MIN_TEMP=220 MAX_TEMP=250 BED_TEMP=80

# 3. Verify
FILAMENT_TAG_READ CHANNEL=0
```

## Troubleshooting

**Tag not detected:**
- Ensure tag is NTAG213/215/216 or Mifare Classic 1K
- Position tag within 1-3cm of reader antenna
- Manually read tag: `FILAMENT_DT_UPDATE CHANNEL=<n>` then `FILAMENT_DT_QUERY CHANNEL=<n>`
- Check `klipper.log` for detection messages

**OpenPrintTag tags don't work:**
- Expected - OpenPrintTag uses ISO15693 which is not supported by U1 hardware
- Use NTAG tags with OpenSpool format instead

**NTAG tags only work on extended firmware:**
- Basic and original firmware only support Mifare Classic 1K with Snapmaker proprietary format
- Extended firmware adds NTAG215/216 support
