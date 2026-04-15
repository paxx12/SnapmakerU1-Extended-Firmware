# Spoolman ↔ RFID Sync Solution for Snapmaker U1 Extended Firmware

## Problem Statement

The Snapmaker U1 Extended Firmware reads RFID tags from multiple formats (Snapmaker, OpenSpool,
TigerTag, Bambu, Creality, Anycubic, etc.) but the internal data model (`FILAMENT_INFO_STRUCT`)
is limited — it loses fields that richer tag formats provide. The user wants:

1. **Expanded data model** — more fields in the internal model, especially transmission distance
   (TD, for HueForge) and material subtypes (marble, wood, metal, silk, etc.)
2. **Spool repository** — a centralized, self-hosted database of all spools with full metadata
3. **Sync** — semi-automatic syncing between U1 RFID scans and the repository via a web UI
4. **Easy tag writing** — use TigerTag mobile app (or similar) to write tags, then import to repo
5. **Wide visibility** — spool data available in Klipper, Snapmaker Orca, Fluidd/Mainsail,
   HueForge, and any other tool that queries the repo

---

## Current Architecture (As-Is)

```
          ┌──────────────────────────────────────────────────────────┐
          │                  Physical RFID Tags                      │
          │  Snapmaker│OpenSpool│TigerTag│Bambu│Creality│Anycubic    │
          └──────────────────────┬───────────────────────────────────┘
                                 │
                ┌────────────────┴─────────────────┐
                │          FM175XX Readers         │
                │  (2 × SPI, 4 antenna coils)      │
                └────────┬────────────────┬────────┘
                         │                │
              ┌──────────▼──────┐   ┌─────▼────────────────┐
              │ Klipper NDEF    │   │ OpenRFID Service     │
              │ Parser (built-  │   │ (external process)   │
              │ in, OpenSpool   │   │ TigerTag, Bambu,     │
              │ JSON only)      │   │ Creality, Snapmaker, │
              └────────┬────────┘   │ Anycubic, Elegoo,    │
                       │            │ OpenSpool, QIDI      │
                       │            └───────┬──────────────┘
                       │                    │
                       │   POST /printer/filament_detect/set
                       │   (webhook_exporter template)
                       │                    │
              ┌────────▼────────────────────▼───────────┐
              │        filament_detect Klipper Object   │
              │  ┌───────────────────────────────────┐  │
              │  │  FILAMENT_INFO_STRUCT[channel]    │  │
              │  │  VENDOR, MAIN_TYPE, SUB_TYPE,     │  │
              │  │  RGB_1, ALPHA, HOTEND_MIN/MAX,    │  │
              │  │  BED_TEMP, CARD_UID, SKU          │  │
              │  │  (10 writable fields)             │  │
              │  └───────────────────────────────────┘  │
              └───────┬───────────────────┬─────────────┘
                      │                   │
           ┌──────────▼───────┐    ┌──────▼───────────────┐
           │ print_task_config│    │ Moonraker REST API   │
           │ (mirrors subset) │    │ /printer/objects/    │
           │ vendor, type,    │    │  query?filament_     │
           │ sub_type, color  │    │  detect              │
           └───────┬──────────┘    └───────┬──────────────┘
                   │                       │
          ┌────────▼───┐   ┌───────────────▼───┐   ┌──────────┐
          │ Snapmaker  │   │ AFC-Lite (Klipper │   │ Fluidd / │
          │ Orca       │   │ UI card)          │   │ Mainsail │
          │ (slicer)   │   │ vendor+type+      │   │ Web UI   │
          │ Uses naming│   │ subtype+color     │   │          │
          │ convention │   │                   │   │          │
          └────────────┘   └───────────────────┘   └──────────┘
```

### Current Data Loss

Fields available in **TigerTag** but **not passed** to consumers:

| TigerTag Field | In internal model? | In webhook template? | Notes |
|---|---|---|---|
| Brand (brand_id) | ✅ VENDOR | ✅ `filament.manufacturer` | |
| Material type | ✅ MAIN_TYPE | ✅ `filament.type` | |
| Aspects (subtypes) | ✅ SUB_TYPE | ✅ `filament.modifiers` | Combined as space-separated |
| Color RGBA | ✅ RGB_1, ALPHA | ✅ `filament.rgb`, `.alpha` | |
| Hotend temps | ✅ HOTEND_MIN/MAX | ✅ `filament.hotend_*_temp_c` | |
| Bed temp | ✅ BED_TEMP | ✅ `filament.bed_temp_c` | |
| Card UID | ✅ CARD_UID | ✅ `scan.uid` | |
| **Diameter** | Read-only, never set | ❌ Not in template | Lost |
| **Weight** | Read-only, never set | ❌ Not in template | Lost |
| **Drying temp** | Read-only, never set | ❌ Not in template | Lost |
| **Drying time** | Read-only, never set | ❌ Not in template | Lost |
| **Mfg date** | Read-only, never set | ❌ Not in template | Lost |
| **Product ID** | ❌ Not in model | ❌ Not in template | Lost |
| **TD / transmission distance** | ❌ Not parsed by OpenRFID | ❌ | **Exists in official TigerTag V1.0 spec but OpenRFID doesn't extract it yet** |
| **Color2 (RGB)** | ❌ Not in model | ❌ | TigerTag V1.0 has 3 colors; only Color1 is parsed |
| **Color3 (RGB)** | ❌ Not in model | ❌ | Same |
| **Bed Temp Min/Max** | ❌ Not parsed | ❌ | TigerTag V1.0 has separate min/max bed temps |
| **Emoji** | ❌ Not in model | ❌ | TigerTag V1.0: 4-byte UTF-8 emoji |
| **Custom Message** | ❌ Not in model | ❌ | TigerTag V1.0: 28-byte free text |

**Critical finding (UPDATED):** The official TigerTag V1.0 spec ([TigerTag-Project/TigerTag-RFID-Guide](https://github.com/TigerTag-Project/TigerTag-RFID-Guide))
**DOES include TD** as a native 2-byte field (value/10, range 0.1–100.0). However, the OpenRFID
TigerTag processor (pinned SHA `a45aacd7`) does **not** parse TD, Color2/3, Bed Temp Min/Max,
Emoji, or Custom Message. The byte layouts differ between the official V1.0 spec and what OpenRFID
currently implements — see the "TigerTag Spec vs OpenRFID Implementation" section below for
details. For tags NOT written with TigerTag (OpenSpool, Bambu, etc.), TD must still come from the
spool repository.

### TigerTag Spec vs OpenRFID Implementation

The official TigerTag V1.0 spec was published on 2025-06-09. OpenRFID (SHA `a45aacd7`) was
written before/independently of this spec. BenGlut (TigerTag team) has contributedJSON
database updates to OpenRFID (PRs #6 and #9, Apr 2026) but byte offsets remain unchanged.

**Byte layout comparison:**

| Offset | OpenRFID (current) | Official TigerTag V1.0 |
|---|---|---|
| 0–3 | TAG_ID (4B) | ID TigerTag (4B) |
| 4–7 | PRODUCT_ID (4B) | ID Product (4B) |
| 8–9 | MATERIAL_ID (2B) | ID Material (2B) |
| 10 | ASPECT1_ID (1B) | **ID Diameter** (1B) |
| 11 | ASPECT2_ID (1B) | **ID Aspect 1** (1B) |
| 12 | TYPE_ID (1B) | **ID Aspect 2** (1B) |
| 13 | DIAMETER_ID (1B) | **ID Type** (1B) |
| 14–15 | BRAND_ID (2B) | ID Brand (2B) |
| 16 | COLOR_RGBA start | **ID Unit** (1B) |
| 16–19 | COLOR_RGBA (4B) | — |
| 17–20 | — | **Color1 RGBA** (4B) |
| 20–22 | WEIGHT (3B) | — |
| 21–23 | — | **Color2 RGB** (3B) |
| 23 | UNIT_ID (1B) | — |
| 24–26 | TEMP_MIN (2B) | **Color3 RGB** (3B) |
| 26–27 | TEMP_MAX (2B) | — |
| 27–28 | — | **TD** (2B) |
| 28 | DRY_TEMP (1B) | — |
| 29 | DRY_TIME (1B) | **Measure** (3B, offset 29–31) |
| 30–31 | (gap) | — |
| 32–35 | TIMESTAMP (4B) | Nozzle Temp Min (1B @32), Max (1B @33), Dry Temp (1B @34), Dry Time (1B @35) |
| 36–37 | — | **Bed Temp Min** (1B @36), **Max** (1B @37) |
| 38–41 | — | **Time Stamp** (4B) |
| 42–53 | — | Reserved (12B) |
| 48 | METADATA offset | — |
| 54–57 | — | **Emoji** (4B) |
| 58–85 | — | **Custom Message** (28B) |
| 80 | SIGNATURE offset | — |
| pages 24–39 | — | **ECDSA Signature** (64B, optional) |

**Key discrepancies:**
1. **Field order at bytes 10–13**: Aspect/Type/Diameter shuffled vs Diameter/Aspect/Type
2. **Unit position**: OpenRFID at byte 23 vs official at byte 16
3. **Color**: OpenRFID has 1 RGBA at 16; official has Unit at 16, then RGBA at 17, plus Color2/3
4. **Temperature sizes**: OpenRFID uses 2-byte temps; official uses 1-byte temps
5. **Missing in OpenRFID**: TD, Color2, Color3, Bed Temp Min/Max, Emoji, Custom Message, Signature

**Implications:**
- Tags written by the TigerTag mobile app (following V1.0 spec) may be **misparsed** by the
  current OpenRFID TigerTag processor if the byte layout is truly different
- OR the V1.0 README table doesn't represent exact byte offsets (the page mapping diagram image
  would be authoritative, but it's not machine-readable)
- **Action needed**: Verify actual tag binary layout by reading a tag written by the TigerTag
  mobile app, or coordinate with TigerTag/OpenRFID maintainers to align
- **For TD**: Even once OpenRFID is updated to parse TD from the tag, tags written without TD
  (or non-TigerTag formats) will still need TD sourced from Spoolman

### Fields Across All Tag Formats

| Field | Snapmaker | OpenSpool | TigerTag | Bambu | Anycubic | Creality |
|---|---|---|---|---|---|---|
| Brand/Vendor | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Material type | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Material subtype | ✅ | ✅ (ext) | ✅ (2 aspects) | ❌ | ❌ | ❌ |
| Color RGBA | ✅ (5 colors) | ✅ (5 colors) | ✅ (3 colors in V1.0) | ✅ | ✅ | ✅ |
| Hotend temp range | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Bed temp | ✅ | ✅ (ext) | **✅ (V1.0 min+max)** | ✅ | ❌ | ✅ |
| Diameter | ✅ | ✅ (ext) | ✅ | ✅ | ❌ | ✅ |
| Weight | ✅ | ✅ (ext) | ✅ | ✅ | ❌ | ✅ |
| Drying temp/time | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ |
| Mfg date | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Product ID | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Density | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Transmission distance** | ❌ | ❌ | **✅ (V1.0 spec, 2B)** | ❌ | ❌ | ❌ |
| **Finish (matte/silk/…)** | Via subtype | Via subtype | Via aspects | ❌ | ❌ | ❌ |
| **Pattern (marble/wood/…)** | Via subtype | Via subtype | Via aspects | ❌ | ❌ | ❌ |

**Conclusion:** TigerTag is the richest tag format supported by the U1. The official V1.0 spec
is even richer than what OpenRFID currently parses — it includes TD, 3 colors, bed temp min/max,
emoji, custom message, and ECDSA signatures. Its aspects system captures subtypes like Marble,
Wood, Metal, Silk, Galaxy, Carbon, etc. **TD IS available on TigerTag V1.0 tags** (if written by
the TigerTag mobile app), but OpenRFID needs updating to extract it. For non-TigerTag formats,
TD must still come from a spool repository. Density is not on any tag format.

**Additional TigerTag V1.0 features (from official spec):**
- **TigerTag+ (cloud sync):** Product ID ≠ 0xFFFFFFFF enables cloud API lookups
  (`api.tigertag.io`) for full product metadata
- **Twin tag linking:** Two tags on the same spool share the same timestamp value for pairing
- **ECDSA-P256 signatures:** Pages 24–39 can hold a 64-byte digital signature for authenticity
  verification. Factory TigerTags from filament manufacturers will include these.
- **Tag variants:**
  - `0x6C41A2E1` = TigerTag Init (blank/initialized)
  - `0x5BF59264` = TigerTag Maker (100% offline)
  - `0xBC0FCB97` = TigerTag+ (offline + optional cloud)
- **Mobile apps:** iOS and Android apps for reading/writing TigerTag format
- **Lookup databases:** JSON files on GitHub + REST API at `api.tigertag.io` for material,
  brand, aspect, diameter, type, unit registries
- **License:** GPLv3 for open-source use; separate OEM license for commercial integration

---

## Spool Repository: Spoolman (Recommended)

### Why Spoolman

| Criteria | Spoolman | Alternatives |
|---|---|---|
| Self-hosted | ✅ Docker | — |
| REST API | ✅ Full CRUD | — |
| Custom fields (`extra`) | ✅ Any key-value + typed fields API | — |
| Moonraker integration | ✅ Native (Moonraker `[spoolman]` config) | — |
| Community | ✅ 2.4k stars, 111 contributors | — |
| External filament DB | ✅ SpoolmanDB (community-sourced) | — |
| Multi-color support | ✅ `multi_color_hexes` | — |
| Weight tracking | ✅ Used/remaining during prints | — |
| HueForge compatibility | Via `extra` fields for TD | — |
| Active development | ✅ v0.23.1, Feb 2025 | — |

There is no other self-hosted spool management tool with this level of maturity and API support.

### Spoolman Data Model (Native + Extended)

**Native filament fields:**

| Field | Type | Maps from RFID |
|---|---|---|
| `name` | string | `"{vendor} {type} {subtype}"` |
| `vendor` → `vendor.name` | string | VENDOR |
| `material` | string | MAIN_TYPE |
| `color_hex` | string | RGB_1 as hex |
| `multi_color_hexes` | string | RGB_2..RGB_5 comma-separated |
| `density` | float | Not on tag; set manually or from SpoolmanDB |
| `diameter` | float (mm) | DIAMETER ÷ 100 |
| `weight` | float (g) | WEIGHT |
| `settings_extruder_temp` | int (°C) | HOTEND_MAX_TEMP |
| `settings_bed_temp` | int (°C) | BED_TEMP |
| `article_number` | string | — |
| `comment` | string | — |
| `extra` | JSON object | Custom fields (see below) |

**Custom extra fields to define in Spoolman** (via `/api/v1/field/filament/{key}`):

| Key | Name | Type | Unit | For |
|---|---|---|---|---|
| `td` | Transmission Distance | `float` | mm | HueForge |
| `subtype` | Material Subtype | `text` | — | Marble, Wood, Metal, Silk, Galaxy, CF, GF, Matte, etc. |
| `hotend_min_temp` | Min Hotend Temp | `integer` | °C | Temperature range (Spoolman only stores one temp) |
| `drying_temp` | Drying Temperature | `integer` | °C | Drying guidance |
| `drying_time` | Drying Time | `integer` | h | Drying guidance |
| `mfg_date` | Manufacturing Date | `text` | — | YYYY-MM-DD |
| `rfid_uid` | RFID Tag UID | `text` | — | UID-based matching between tag and spool |
| `tigertag_product_id` | TigerTag Product ID | `text` | — | Cross-reference to TigerTag database |

**Native spool fields:**

| Field | Type | Notes |
|---|---|---|
| `filament_id` | int | References the filament type |
| `initial_weight` | float (g) | Starting weight |
| `remaining_weight` | float (g) | Auto-tracked by Moonraker during prints |
| `used_weight` | float (g) | Auto-tracked |
| `location` | string | e.g. "Snapmaker U1 / E0" |
| `lot_nr` | string | Batch number |
| `comment` | string | Contains `rfid:XXXX` for UID matching |
| `extra` | JSON | Custom fields |

**Custom extra fields for spool:**

| Key | Name | Type | Notes |
|---|---|---|---|
| `rfid_uid` | RFID Tag UID | `text` | Duplicated here for querying at spool level |
| `tigertag_product_id` | TigerTag Product ID | `text` | Per-spool product identifier |

### Spoolman External Filament Database

Spoolman's external filament DB (`/api/v1/external/filament`) already includes:
- `finish`: matte, silk, glossy
- `pattern`: marble, wood, galaxy
- `translucent`: boolean
- `glow`: boolean

These map well to TigerTag aspects. When importing from SpoolmanDB, these properties can be
auto-populated to the `extra` fields.

---

## Proposed Architecture (To-Be)

```
          ┌─────────────────────────────────────────────────────────┐
          │                  Physical RFID Tags                     │
          │  Snapmaker│OpenSpool│TigerTag│Bambu│Creality│Anycubic   │
          └──────────────────────┬──────────────────────────────────┘
                                 │
                ┌────────────────┴─────────────────┐
                │          FM175XX Readers          │
                └────────┬────────────────┬────────┘
                         │                │
              ┌──────────▼──────┐   ┌─────▼──────────────┐
              │ Klipper NDEF    │   │ OpenRFID Service    │
              │ Parser          │   │                     │
              └────────┬────────┘   └───────┬─────────────┘
                       │                    │
                       │  POST /printer/filament_detect/set
                       │  ┌─────────────────────────────────┐
                       │  │ EXPANDED webhook template:      │
                       │  │ + DIAMETER, WEIGHT,              │
                       │  │ + DRYING_TEMP, DRYING_TIME,      │
                       │  │ + MF_DATE                        │
                       │  └─────────────────────────────────┘
                       │                    │
              ┌────────▼────────────────────▼─────────┐
              │  filament_detect (EXPANDED model)      │
              │  ┌──────────────────────────────────┐  │
              │  │  Writable: VENDOR, MAIN_TYPE,     │  │
              │  │  SUB_TYPE, RGB_1..5, ALPHA,       │  │
              │  │  HOTEND_MIN/MAX, BED_TEMP,        │  │
              │  │  CARD_UID, SKU,                   │  │
              │  │  + DIAMETER, WEIGHT, DRYING_TEMP, │  │
              │  │  + DRYING_TIME, MF_DATE           │  │  ← NEW writable
              │  └──────────────────────────────────┘  │
              └───┬───────────────────┬────────────────┘
                  │                   │
       ┌──────────▼───────┐   ┌──────▼──────────────┐
       │ print_task_config│   │ Moonraker REST API   │
       │ (unchanged —     │   │ (returns all fields) │
       │ backward compat) │   │                      │
       └──────┬───────────┘   └──────┬───────────────┘
              │                      │
     ┌────────▼──┐   ┌──────────────▼──┐   ┌──────────┐
     │ Snapmaker  │   │ AFC-Lite        │   │ Fluidd / │
     │ Orca       │   │ (unchanged)     │   │ Mainsail │
     │(unchanged) │   │                 │   │          │
     └────────────┘   └─────────────────┘   └──────────┘
                                │
                                │ reads filament_detect
                                ▼
      ┌─────────────────────────────────────────────────────────┐
      │          RFID Spools Web App (on printer/Klipper)       │
      │  (nginx-served page, accessed via browser)              │
      │                                                         │
      │  1. Polls filament_detect for current tag data          │
      │  2. Shows expanded spool info (all fields incl. TD)     │
      │  3. User clicks "Sync to Spoolman" per channel          │
      │     → match by UID or import as new spool               │
      │  4. User clicks "Link to Existing" to bind UID          │
      │  5. User clicks "Set Active" to assign in Moonraker     │
      │  6. TD, drying, density editable before sync            │
      │                                                         │
      └───────────────────────┬─────────────────────────────────┘
                              │
                   ┌──────────▼──────────┐
                   │     Spoolman        │
                   │  (self-hosted)      │
                   │                     │
                   │  Filament:          │
                   │   name, vendor,     │
                   │   material, color,  │
                   │   diameter, weight, │
                   │   density, temps    │
                   │   extra:            │
                   │    td, subtype,     │
                   │    drying_temp/time │
                   │    rfid_uid,        │
                   │    mfg_date         │
                   │                     │
                   │  Spool:             │
                   │   remaining_weight, │
                   │   location,         │
                   │   lot_nr,           │
                   │   extra: rfid_uid   │
                   │                     │
                   └──────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Consumers:        │
                    │  • HueForge (TD)   │
                    │  • Spoolman Web UI │
                    │  • RFID Spools App │
                    │  • Home Assistant  │
                    │  • Prometheus      │
                    └────────────────────┘

      ┌─────────────────────────────────────────────────────────┐
      │              Tag Writing Workflow                        │
      │                                                         │
      │  Phone (TigerTag app)  ──write──▶  NFC Tag              │
      │                                      │                  │
      │                                      │ place on U1      │
      │                                      ▼                  │
      │                              RFID Reader scans tag      │
      │                                      │                  │
      │                              User opens RFID Spools     │
      │                              web app, reviews data,     │
      │                              clicks "Sync to Spoolman" │
      │                                                         │
      └─────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Component Overview

| # | Component | Type | Effort | Description |
|---|---|---|---|---|
| 0 | Align OpenRFID TigerTag parser with V1.0 spec | Upstream PR / fork | Medium | Update byte offsets, add TD/Color2/3/BedTemp/Emoji/Message parsing |
| 1 | Expand `filament_detect/set` | Firmware patch | Small | Make DIAMETER, WEIGHT, DRYING_TEMP, DRYING_TIME, MF_DATE, TD writable |
| 2 | Expand OpenRFID webhook templates | Config change | Small | Pass all available fields in the webhook template (including TD) |
| 3 | Spoolman custom fields setup | Script | Small | Define extra fields (td, subtype, drying, rfid_uid, etc.) |
| 4 | RFID Spools web app with sync | Enhanced web app | Medium | Expanded spool info page with user-triggered Spoolman sync |
| 5 | Spoolman deployment overlay | Firmware overlay | Small | Optional Spoolman Docker deployment on U1 or docs for external |

### Component 0: Align OpenRFID TigerTag Parser with V1.0 Spec

**What:** The OpenRFID TigerTag processor (SHA `a45aacd7`) has a different byte layout from the
official TigerTag V1.0 spec. Fields at bytes 10–13 are in different order, Color2/3 and TD are
not parsed, temps use 2 bytes instead of 1, and bed temp is missing.

**Why:** Tags written by the TigerTag mobile app (V1.0 spec) may be misparsed by the current
OpenRFID processor. Additionally, TD on the tag is completely lost.

**Options:**

  a. **Upstream PR to OpenRFID** — Contribute the V1.0 byte layout fix to
     `suchmememanyskill/OpenRFID`. BenGlut (TigerTag team) already contributes there.
     → Preferred approach.

  b. **Fork/patch locally** — Create a patch in overlay 64-app-openrfid to fix the constants
     and processor, like the existing Klipper patches.

**Prerequisite:** Verify actual tag binary layout by scanning a tag written by the TigerTag mobile
app and dumping raw bytes. This confirms whether the official README byte ordering is accurate
or if the page mapping diagram shows a different layout.

**Files affected:**
- `src/tag/tigertag/constants.py` — byte offsets
- `src/tag/tigertag/processor.py` — parse TD, Color2/3, BedTemp, Emoji, Message
- `src/filament/generic.py` — add `td`, `colors` (expanded), `bed_temp_min_c`, `bed_temp_max_c`

### Component 1: Expand `filament_detect/set` Endpoint

**What:** Promote read-only fields `DIAMETER`, `WEIGHT`, `DRYING_TEMP`, `DRYING_TIME`, `MF_DATE`
to writable via the `/printer/filament_detect/set` API. Also add a new `TD` field for
transmission distance (not currently in FILAMENT_INFO_STRUCT at all).

**Why:** The OpenRFID webhook exporter can only set writable fields. Currently these are read-only
so TigerTag's diameter, weight, drying info, and manufacturing date are all lost when OpenRFID
posts tag data.

**How:** Modify `filament_detect.py` patch (overlay 13-patch-rfid) to accept these additional keys
in the `set` handler's whitelist.

**Backward compatibility:** Fully backward compatible — existing clients that don't send these
fields are unaffected. `print_task_config` continues to mirror only vendor/type/subtype/color.

**Files to modify:**
- `overlays/firmware-extended/13-patch-rfid/patches/05-add-filament-detect-set-endpoint.patch`
- `docs/design/filament_detect.md` (update docs)

### Component 2: Expand OpenRFID Webhook Templates

**What:** Update the base config and vendor/generic configs to pass all available fields.

**Files to modify:**
- `overlays/firmware-extended/64-app-openrfid/root/usr/local/share/openrfid/extended/openrfid_u1_vendor.cfg`
- `overlays/firmware-extended/64-app-openrfid/root/usr/local/share/openrfid/extended/openrfid_u1_generic.cfg`

**Current template** (missing fields):
```jinja
"VENDOR": "{{filament.manufacturer}}",
"MAIN_TYPE": "{{ filament.type }}",
"SUB_TYPE": "{{ filament.modifiers | join(' ') }}",
"HOTEND_MIN_TEMP": {{ filament.hotend_min_temp_c | int }},
"HOTEND_MAX_TEMP": {{ filament.hotend_max_temp_c | int }},
"BED_TEMP": {{ filament.bed_temp_c | int }},
"ALPHA": {{ filament.alpha }},
"RGB_1": {{ filament.rgb }},
"CARD_UID": [...]
```

**Expanded template** (all available GenericFilament fields):
```jinja
"VENDOR": "{{filament.manufacturer}}",
"MAIN_TYPE": "{{ filament.type }}",
"SUB_TYPE": "{{ filament.modifiers | join(' ') }}",
"HOTEND_MIN_TEMP": {{ filament.hotend_min_temp_c | int }},
"HOTEND_MAX_TEMP": {{ filament.hotend_max_temp_c | int }},
"BED_TEMP": {{ filament.bed_temp_c | int }},
"ALPHA": {{ filament.alpha }},
"RGB_1": {{ filament.rgb }},
"CARD_UID": [...],
"DIAMETER": {{ filament.diameter_mm | default(175, true) | int }},
"WEIGHT": {{ filament.weight_g | default(0, true) | int }},
"DRYING_TEMP": {{ filament.dry_temp_c | default(0, true) | int }},
"DRYING_TIME": {{ filament.dry_time_h | default(0, true) | int }},
"TD": {{ filament.td | default(0, true) }}
```

> **Note:** The `filament.td` attribute will only be available once OpenRFID's TigerTag processor
> is updated (Component 0). Until then, TD from TigerTag tags is lost in the OpenRFID pipeline.
> The exact GenericFilament attribute names must be verified against the OpenRFID source.

### Component 3: Spoolman Custom Fields Setup

**What:** A one-time setup script or overlay that configures Spoolman's extra fields via its API.

**Spoolman extra field definitions:**

```bash
# Filament-level extra fields
curl -X POST http://spoolman:7912/api/v1/field/filament/td \
  -H 'Content-Type: application/json' \
  -d '{"name": "Transmission Distance", "field_type": "float", "unit": "mm", "order": 1}'

curl -X POST http://spoolman:7912/api/v1/field/filament/subtype \
  -H 'Content-Type: application/json' \
  -d '{"name": "Subtype", "field_type": "choice", "order": 2, "choices": [
    "Basic", "Matte", "Silk", "Metal", "Marble", "Wood", "Galaxy", "Carbon",
    "CF", "GF", "Translucent", "Glow", "Fluo", "Pro", "Rapid", "HF",
    "Ultra", "AERO", "Odorless", "Support", "95A", "95A HF"
  ]}'

curl -X POST http://spoolman:7912/api/v1/field/filament/hotend_min_temp \
  -H 'Content-Type: application/json' \
  -d '{"name": "Min Hotend Temp", "field_type": "integer", "unit": "°C", "order": 3}'

curl -X POST http://spoolman:7912/api/v1/field/filament/drying_temp \
  -H 'Content-Type: application/json' \
  -d '{"name": "Drying Temperature", "field_type": "integer", "unit": "°C", "order": 4}'

curl -X POST http://spoolman:7912/api/v1/field/filament/drying_time \
  -H 'Content-Type: application/json' \
  -d '{"name": "Drying Time", "field_type": "integer", "unit": "h", "order": 5}'

curl -X POST http://spoolman:7912/api/v1/field/filament/mfg_date \
  -H 'Content-Type: application/json' \
  -d '{"name": "Manufacturing Date", "field_type": "text", "order": 6}'

# Spool-level extra fields
curl -X POST http://spoolman:7912/api/v1/field/spool/rfid_uid \
  -H 'Content-Type: application/json' \
  -d '{"name": "RFID Tag UID", "field_type": "text", "order": 1}'

curl -X POST http://spoolman:7912/api/v1/field/spool/tigertag_product_id \
  -H 'Content-Type: application/json' \
  -d '{"name": "TigerTag Product ID", "field_type": "text", "order": 2}'
```

### Component 4: RFID Spools Web App (with Spoolman Sync)

**What:** A semi-automatic approach: a dedicated web page served from the printer (via nginx),
accessible alongside Fluidd/Mainsail, that shows expanded spool info from RFID tags and gives
the user control over when and how to sync with Spoolman. No background daemon — the user
reviews tag data and triggers sync actions explicitly.

**Why semi-automatic instead of fully automatic:**
- User retains control — can review/edit data before it hits the repository
- Can correct misidentified filaments, add TD, adjust subtypes before import
- No risk of creating duplicate spools from re-reads or brief tag disconnects
- Simpler implementation — no daemon, no websocket subscription, just a web app
- Same web app that already displays tag data now also handles sync

**The existing app already implements:**
- ✅ 4-channel RFID display with all basic fields
- ✅ Spoolman URL config with proxy
- ✅ UID-based and property-based spool matching
- ✅ Import to Spoolman (vendor, material, subtype, color, temps, weight, diameter)
- ✅ Link to existing spool (stores `rfid:UID` in comment)
- ✅ Set active spool in Moonraker

**Enhancements needed:**

| Feature | Current | Enhanced |
|---|---|---|
| Display drying info | ❌ Shows if present | ✅ Always show from expanded model |
| Display diameter/weight | ❌ Shows if present | ✅ Always show from expanded model |
| Display mfg date | ❌ | ✅ |
| Display TD | ❌ | ✅ Show from tag (if TigerTag) or Spoolman |
| TD input on import | ❌ | ✅ Editable field, pre-filled from tag if available |
| Subtype as dropdown | ❌ Free text | ✅ Dropdown with TigerTag aspects |
| Sync status indicator | ❌ | ✅ Show if spool is synced/unsynced/matched |
| Per-channel sync button | ❌ | ✅ "Sync to Spoolman" per channel |
| Bulk sync | ❌ | ✅ "Sync all to Spoolman" button |
| UID storage | Comment hack | `extra.rfid_uid` field |
| Show Spoolman TD | ❌ | ✅ Display + edit TD from Spoolman spool data |
| HueForge export hint | ❌ | ✅ Show CSV-ready TD data |
| Editable fields before sync | ❌ | ✅ Override any field before importing |

**User workflow (per channel):**

1. Load a spool with RFID tag into the printer
2. Open the RFID Spools web page (e.g. `http://printer/rfid-spools/`)
3. Page polls `filament_detect` via Moonraker — shows all tag fields for each channel
4. If Spoolman is configured, the app auto-checks for UID matches:
   - **Match found** → shows "Linked to Spool #123 (Polymaker PLA Matte)" with a
     "Set Active" button to assign it as Moonraker's active spool
   - **No match** → shows "Not in Spoolman" with three options:
     a. **"Import to Spoolman"** — pre-fills all fields from the tag; user can edit TD,
        subtype, weight, etc. before confirming. Creates vendor (if needed), filament, and
        spool in Spoolman. Stores UID in `spool.extra.rfid_uid`.
     b. **"Link to Existing"** — search Spoolman by vendor/material/color to find an existing
        spool and bind this tag's UID to it
     c. **"Ignore"** — do nothing, keep using tag data in Klipper only
5. After import/link, the "Set Active" button auto-triggers to assign the spool in Moonraker

**Data mapping (tag → Spoolman, user-editable before sync):**

| Tag field | Spoolman field | Editable | Notes |
|---|---|---|---|
| VENDOR | vendor.name | ✅ | Find-or-create vendor |
| MAIN_TYPE | filament.material | ✅ | |
| SUB_TYPE | filament.extra.subtype | ✅ dropdown | TigerTag aspect list |
| RGB_1 | filament.color_hex | ✅ color picker | Convert int → hex |
| ALPHA | filament.color_hex (suffix) | ✅ | Append as alpha channel |
| HOTEND_MIN_TEMP | filament.extra.hotend_min_temp | ✅ | |
| HOTEND_MAX_TEMP | filament.settings_extruder_temp | ✅ | |
| BED_TEMP | filament.settings_bed_temp | ✅ | |
| DIAMETER | filament.diameter | ✅ | mm |
| WEIGHT | filament.weight + spool.initial_weight | ✅ | |
| DRYING_TEMP | filament.extra.drying_temp | ✅ | |
| DRYING_TIME | filament.extra.drying_time | ✅ | |
| MF_DATE | filament.extra.mfg_date | ✅ | |
| TD | filament.extra.td | ✅ | Pre-filled from TigerTag if available |
| CARD_UID | spool.extra.rfid_uid | ❌ auto | Hex string, set automatically |

**Where TD comes from:**
- TD **IS available on TigerTag V1.0 tags** (2 bytes, value/10, range 0.1–100.0) — but ONLY
  if (a) the tag was written with the TigerTag app/spec, AND (b) OpenRFID is updated to parse
  the TD field. Once available, the web app pre-fills it in the import form.
- For **non-TigerTag formats** (OpenSpool, Bambu, Creality, etc.): user enters TD manually in
  the import form, or it can be looked up from SpoolmanDB.
- The import form always shows a TD input field — pre-filled if the tag has it, blank otherwise.
- Future: auto-suggest TD from SpoolmanDB's external filament database when not on tag.

**Implementation:** Pure client-side HTML/CSS/JS (single `index.html`), served via nginx. All
Spoolman and Moonraker calls are made from the browser through the existing nginx proxy.
No server-side daemon or Python process needed.

### Component 5: Spoolman Deployment

**Option A — External Spoolman (recommended):**
Run Spoolman on a separate machine (NAS, Raspberry Pi, etc.) via Docker:
```yaml
# docker-compose.yml
services:
  spoolman:
    image: ghcr.io/donkie/spoolman:latest
    restart: unless-stopped
    ports:
      - "7912:8000"
    volumes:
      - ./data:/home/app/.local/share/spoolman
```

Configure Moonraker on U1:
```ini
# /oem/printer_data/config/moonraker.conf (or include)
[spoolman]
server: http://spoolman-host:7912
sync_rate: 5
```

**Option B — On U1 (Docker not available):**
The U1 runs BusyBox Linux without Docker. Spoolman could potentially run directly with Python +
SQLite, but this is not recommended due to U1's limited resources. Use Option A.

**Nginx proxy on U1** (already exists for the RFID Spools app):
Add a Spoolman reverse proxy route in the nginx overlay for CORS-free browser access.

---

## Tag Writing Workflow

### Recommended: TigerTag Mobile App

1. Install TigerTag app on [Android](https://play.google.com/store/apps/details?id=com.tigertag.connect)
   or [iOS](https://apps.apple.com/fr/app/tigertag-rfid-connect/id6745437963)
2. Enter filament details: brand, material type, aspects (Marble, Wood, etc.), color, temps,
   weight, diameter, drying info, **and TD if known** (the app supports it per V1.0 spec)
3. Write to NTAG213 tag (TigerTag spec fits in 144 bytes of NTAG213)
4. Place tag on spool
5. Load spool into U1 — tag is auto-read
6. Open RFID Spools web page — review tag data, edit TD/subtype if needed
7. Click "Import to Spoolman" — spool is created with all metadata including TD

### Alternative: OpenSpool JSON (simpler tags)

1. Use printtag-web.pages.dev or any NDEF writing app
2. Write OpenSpool JSON to NTAG215 tag:
   ```json
   {
     "protocol": "openspool",
     "version": "1.0",
     "brand": "Generic",
     "type": "PLA",
     "subtype": "Marble",
     "color_hex": "#AABBCC",
     "min_temp": 200,
     "max_temp": 220,
     "bed_min_temp": 55,
     "weight": 1000,
     "diameter": 1.75
   }
   ```
3. Same workflow: open RFID Spools web page → review → import to Spoolman

### Getting TD Values

| Source | Method |
|---|---|
| **TigerTag V1.0 tag** | Written to tag as 2-byte field; auto-read by updated OpenRFID |
| Measure yourself | Print TD calibration model, measure with calipers |
| HueForge community | Download TD spreadsheets from HueForge Discord/docs |
| SpoolmanDB | Some filaments in SpoolmanDB include optical properties |
| Manual entry | Enter in Spoolman UI or RFID Spools app during import |
| TD1S device | BIQU AJAX TD1S V1.0 hardware for measuring TD |

---

## Compatibility Matrix

How each consumer is affected by the expanded model:

| Consumer | Impact | Action needed |
|---|---|---|
| **Snapmaker Orca** (slicer) | None | Uses only `vendor/type/subtype/color` via `print_task_config` — unchanged |
| **U1 Touchscreen** | None | Uses `print_task_config` — unchanged |
| **AFC-Lite** (Klipper card) | None | Uses only `vendor/type/subtype/color` from `print_task_config` — unchanged |
| **Fluidd / Mainsail** | None | Displays whatever `filament_detect` returns — more fields = richer display |
| **OpenRFID** | Template update | Expanded template sends more fields — backward compatible |
| **RFID Spools App** | Central piece | Expanded spool info + user-triggered Spoolman sync |
| **HueForge** | Via Spoolman | Query Spoolman API or export CSV with TD values |
| **Moonraker** | None | Proxies `filament_detect` state — transparent to additional fields |

---

## Summary of Decisions

1. **Spool repository:** Spoolman (self-hosted, Docker, full REST API, custom fields)
2. **Tag format for writing:** TigerTag preferred (most fields), OpenSpool acceptable (simpler)
3. **Internal model expansion:** Make 5 read-only fields writable in `filament_detect/set` + add TD
4. **Transmission distance:** Available on TigerTag V1.0 tags (once OpenRFID parses it); stored
   in Spoolman `extra.td`; for non-TigerTag formats, must be entered manually or sourced from DB
5. **Sync approach:** Semi-automatic — RFID Spools web page shows expanded tag data, user
   triggers sync to Spoolman with review/edit before import (no background daemon)
6. **Tag writing:** TigerTag mobile app (most fields) or OpenSpool web tool (simplest)
7. **Backward compatibility:** All existing consumers (Orca, touchscreen, AFC) work unchanged

---

## File / Overlay Structure

```
overlays/firmware-extended/
├── 13-patch-rfid/             ← MODIFY: expand writable fields in set endpoint
│   └── patches/
│       └── 05-add-filament-detect-set-endpoint.patch
├── 64-app-openrfid/           ← MODIFY: expand webhook template
│   └── root/usr/local/share/openrfid/extended/
│       ├── openrfid_u1_vendor.cfg
│       └── openrfid_u1_generic.cfg
└── 68-app-rfid-spools/        ← NEW: RFID Spools web app overlay (includes sync UI)
    ├── root/
    │   ├── etc/nginx/conf.d/rfid-spools.d/
    │   │   └── rfid-spools.conf       ← nginx route + Spoolman proxy
    │   └── usr/local/share/rfid-spools/
    │       └── html/
    │           └── index.html          ← RFID Spools web app with Spoolman sync
    └── scripts/
        └── 01-setup.sh
```
