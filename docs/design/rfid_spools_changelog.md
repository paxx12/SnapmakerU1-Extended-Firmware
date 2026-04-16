# RFID Spools — Implementation Changelog

This document describes all the changes made for the RFID Spools feature set:
extended RFID data model, TigerTag TD extraction, Spoolman integration web UI,
and the development push tooling. Written for future reference when stabilising
or merging upstream.

> **Branch:** `feat/rfid-sync-expanded`
> **Status:** development / live-testing on a single U1

---

## Table of Contents

1. [Overview](#overview)
2. [Component Map](#component-map)
3. [Overlay: 68-app-rfid-spools (new)](#overlay-68-app-rfid-spools)
4. [Overlay: 64-app-openrfid (modified)](#overlay-64-app-openrfid)
5. [Overlay: 13-patch-rfid (modified)](#overlay-13-patch-rfid)
6. [Dev Tooling: push-rfid-sync.sh](#dev-tooling-push-rfid-syncsh)
7. [Data Flow](#data-flow)
8. [Known Issues & Future Work](#known-issues--future-work)

---

## Overview

The stock Snapmaker U1 Extended Firmware reads RFID tags via OpenRFID, but the
internal Klipper data model (`FILAMENT_INFO_STRUCT`) is limited. These changes:

- **Expand the data model** — add DIAMETER, WEIGHT, DRYING_TEMP, DRYING_TIME,
  MF_DATE, and TD (transmission distance) to `filament_detect/set`.
- **Extract TigerTag TD + bed temp** — patch OpenRFID to parse TD from bytes
  44-45 and bed temp from bytes 30-31 of TigerTag V1.0 user data.
- **Provide a web UI** — "RFID Spools" page at `/rfid-spools/` that shows all
  4 channels with 12+ fields each and offers semi-automatic Spoolman sync.
- **CORS-free Spoolman proxy** — dynamic nginx reverse proxy using the
  `X-Spoolman-Target` header pattern (no server-side URL config needed).
- **Re-read / log actions** — restart OpenRFID and fetch syslog from the UI via
  the firmware-config action API.

---

## Component Map

```
overlays/firmware-extended/
├── 13-patch-rfid/
│   └── patches/
│       └── 05-add-filament-detect-set-endpoint.patch   ← extended fields
│
├── 64-app-openrfid/
│   ├── patches/usr/local/share/openrfid/
│   │   └── 03-add-tigertag-td-and-bed-temp.patch       ← TD extraction
│   └── root/usr/local/share/openrfid/extended/
│       ├── openrfid_u1_vendor.cfg                       ← webhook template
│       └── openrfid_u1_generic.cfg                      ← webhook template
│
└── 68-app-rfid-spools/                                  ← NEW overlay
    └── root/
        ├── etc/nginx/fluidd.d/
        │   └── rfid-spools.conf                         ← nginx config
        ├── usr/local/bin/
        │   └── setup-spoolman-fields.sh                 ← Spoolman field setup
        └── usr/local/share/
            ├── firmware-config/functions/
            │   └── 25_actions_rfid_spools.yaml          ← re-read/log actions
            └── rfid-spools/html/
                └── index.html                           ← web UI (~1300 lines)

scripts/dev/
└── push-rfid-sync.sh                                    ← live deployment tool
```

---

## Overlay: 68-app-rfid-spools

**Purpose:** Self-contained overlay for the RFID Spools web application.

### `root/usr/local/share/rfid-spools/html/index.html`

Single-page web application served at `http://<printer-ip>/rfid-spools/`.

**Key features:**
- Reads all 4 channels from `GET /printer/objects/query?filament_detect`
- Displays 12+ fields per channel: vendor, material, subtype, color (swatch),
  hotend temp range, bed temp, diameter, weight, drying temp/time, TD,
  manufacturing date, RFID UID, official flag
- Spoolman integration panel:
  - Configurable base URL (saved in `localStorage`)
  - Match-by-UID (`rfid:<hex>` in spool comment), then by vendor+material+color
  - "Set active", "Re-link", "Unlink" per spool
  - "Setup Spoolman Custom Fields" button for one-time field creation
- Debug log pane: fetches klippy.log (via Moonraker file API), OpenRFID syslog
  (via firmware-config action API), and live `filament_detect` state
- Re-read Tags button: restarts OpenRFID to force re-scan of all inserted tags
- Moonraker JWT auth: reads `access_token` from localStorage (set by Fluidd)
- Styled to match firmware-config (dark theme, CSS variables)

### `root/etc/nginx/fluidd.d/rfid-spools.conf`

Nginx config included by the main `fluidd.conf`. Three location blocks:

| Location | Purpose |
|---|---|
| `/rfid-spools/` | Serves the static HTML from `/usr/local/share/rfid-spools/html/` |
| `/rfid-spools/spoolman/` | Dynamic reverse proxy to Spoolman. Reads the target URL from the `X-Spoolman-Target` request header. This avoids CORS by keeping all browser requests same-origin. |

**Why this pattern:** The Spoolman URL is user-configurable and can change. Baking
it into nginx config would require a restart. Instead, the browser sends the URL in
a custom header and nginx proxies to it dynamically using `set $sm_target $http_x_spoolman_target`.

### `root/usr/local/bin/setup-spoolman-fields.sh`

Shell script that creates custom extra fields in Spoolman via `POST /api/v1/field`.
Creates fields on the `spool` and `filament` entities for TD, subtype, drying temp,
drying time, etc. Idempotent — re-running gets 409 (harmless).

### `root/usr/local/share/firmware-config/functions/25_actions_rfid_spools.yaml`

Registers two actions in the firmware-config action API:

| Action ID | Command | Purpose |
|---|---|---|
| `restart-openrfid` | `/etc/init.d/S99openrfid restart` | Force re-read of all RFID tags |
| `openrfid-log` | `logread \| grep -i openrfid \| tail -80` | Fetch recent syslog entries |

**Why firmware-config API:** Moonraker's `/machine/proc/exec` is not enabled on
the U1 (returns 404). The firmware-config service (port 9091, proxied at
`/firmware-config/api/`) already has an action execution framework that runs
commands and streams output. This provides a safe, authenticated alternative.

---

## Overlay: 64-app-openrfid

### `patches/usr/local/share/openrfid/03-add-tigertag-td-and-bed-temp.patch`

**New file.** Applied at build time against the OpenRFID source (pinned at SHA
`a45aacd7`). Modifies three OpenRFID source files:

#### `tag/tigertag/constants.py`
Adds three offset constants per TigerTag V1.0 spec:
- `OFF_BED_TEMP_MIN = 30` — bed temperature minimum (1 byte, °C)
- `OFF_BED_TEMP_MAX = 31` — bed temperature maximum (1 byte, °C)
- `OFF_TD = 44` — transmission distance (2 bytes, big-endian uint16, value/10 = mm)

#### `tag/tigertag/processor.py`
Extracts the new fields during tag parsing:
- Reads `bed_temp_min` and `bed_temp_max` from user data bytes 30-31
- Reads TD as uint16 big-endian from bytes 44-45, validates range 1-1000, divides
  by 10 to get mm
- Passes `bed_temp_c=float(max(bed_temp_min, bed_temp_max))` and `td=td_mm` to
  `GenericFilament`

#### `filament/generic.py`
Adds `td: float = 0.0` keyword parameter to `GenericFilament.__init__()` with a
default value so existing tag processors (Snapmaker, Bambu, Creality, etc.) are
**not affected**. Adds `td` to `to_dict()` and `pretty_text()`.

### `root/usr/local/share/openrfid/extended/openrfid_u1_vendor.cfg`

Webhook template for "openrfid" mode (vendor-aware). Maps `GenericFilament`
attributes to `filament_detect/set` JSON fields. Extended fields added:

```
"DIAMETER": {{ (filament.diameter_mm * 100) | int }},
"WEIGHT": {{ filament.weight_grams | int }},
"DRYING_TEMP": {{ filament.drying_temp_c | int }},
"DRYING_TIME": {{ filament.drying_time_hours | int }},
"MF_DATE": "{{ filament.manufacturing_date }}",
"TD": {{ filament.td | default(0, true) }}
```

Note: `DIAMETER` is stored as mm×100 integer (e.g. `175` = 1.75 mm) to match the
existing `FILAMENT_INFO_STRUCT` convention.

### `root/usr/local/share/openrfid/extended/openrfid_u1_generic.cfg`

Same extended fields as vendor config, but forces vendor to "Generic" for non-
Snapmaker tags (used in "openrfid-generic" mode).

---

## Overlay: 13-patch-rfid

### `patches/05-add-filament-detect-set-endpoint.patch`

**Modified.** This build-time patch against Klipper's `filament_detect.py` adds the
`POST /printer/filament_detect/set` HTTP endpoint. The patch was extended to accept
six additional fields beyond the original set:

| Field | Type | Added by this change |
|---|---|---|
| `VENDOR` | `str` | (original) |
| `MAIN_TYPE` | `str` | (original) |
| `SUB_TYPE` | `str` | (original) |
| `HOTEND_MIN_TEMP` | `int` | (original) |
| `HOTEND_MAX_TEMP` | `int` | (original) |
| `BED_TEMP` | `int` | (original) |
| `ALPHA` | `int` | (original) |
| `RGB_1` | `int` | (original) |
| `CARD_UID` | `list[int]` | (original) |
| `SKU` | `int` | (original) |
| `DIAMETER` | `int` | **new** |
| `WEIGHT` | `int` | **new** |
| `DRYING_TEMP` | `int` | **new** |
| `DRYING_TIME` | `int` | **new** |
| `MF_DATE` | `str` | **new** |
| `TD` | `float` | **new** |

**Important:** These new fields are not part of the stock `FILAMENT_INFO_STRUCT`
dict from `filament_protocol.py`. The handler adds them dynamically to the
`filament_info` dict copy. Moonraker exposes whatever keys are in the dict, so
they appear in `GET /printer/objects/query?filament_detect` responses.

Any unknown fields are still rejected with an error to prevent silent data loss.

---

## Dev Tooling: push-rfid-sync.sh

**Location:** `scripts/dev/push-rfid-sync.sh`

Deploys all RFID Spools changes to a live printer over SSH without rebuilding
firmware. Designed for iterative development.

### Steps

| Step | What | How |
|---|---|---|
| 1 | Push webhook templates | `scp` vendor + generic `.cfg` files |
| 1b | Apply TigerTag TD patch | `patch -p1` against OpenRFID source on printer. Pipes through `tr -d '\r'` to handle Windows CRLF. Idempotent (checks `grep -q 'self.td'`). |
| 2 | Patch filament_detect.py | Injects extended field handlers (DIAMETER, WEIGHT, etc.) into the existing `/set` endpoint. Uses a Python patcher script (`scp` + `python3`) to find the "unsupported fields" guard and insert code before it. Idempotent (checks `grep -q 'DRYING_TEMP'`). |
| 3 | Push web app | `tar` the entire `68-app-rfid-spools/root/` tree to `/` on the printer. Includes nginx config, HTML, firmware-config YAML, and setup script. |
| 4 | Set permissions | `chmod +x` on the Spoolman setup script |
| 5 | Restart services | firmware-config → Klipper → OpenRFID → nginx reload |

### Why the Python patcher for step 2

The build-time patch (`05-add-filament-detect-set-endpoint.patch`) targets the
stock `filament_detect.py`. On a live printer that already has the base `/set`
handler (from a prior firmware build), the patch context doesn't match. Instead
of a traditional `patch` command, we send a small Python script that does a
targeted string replacement — finding the "unsupported fields" guard and inserting
the new field handlers before it. This is version-tolerant and avoids SSH
quoting issues.

---

## Data Flow

```
  ┌─────────────────┐
  │  Physical Tag    │  (TigerTag, Snapmaker, OpenSpool, Bambu, etc.)
  └────────┬────────┘
           │ SPI read
  ┌────────▼────────┐
  │    OpenRFID     │  tag/tigertag/processor.py (TD + bed temp patch)
  │                 │  tag/snapmaker/processor.py (HKDF key from fw)
  │                 │  filament/generic.py (td=0.0 default)
  └────────┬────────┘
           │ webhook_exporter (Jinja2 template)
           │ POST /printer/filament_detect/set
           │ {channel, info: {VENDOR, MAIN_TYPE, ..., DIAMETER, WEIGHT,
           │  DRYING_TEMP, DRYING_TIME, MF_DATE, TD}}
  ┌────────▼────────────────────────────────────┐
  │  filament_detect.py (Klipper)               │
  │  _handle_filament_detect_set()              │
  │  → stores in FILAMENT_INFO_STRUCT + extras  │
  └────────┬────────────────────────────────────┘
           │ GET /printer/objects/query?filament_detect
  ┌────────▼───────────────────────┐
  │  RFID Spools Web UI            │ (/rfid-spools/)
  │  index.html                    │
  │  → displays 12+ fields        │
  │  → matches to Spoolman spools │
  │  → sync via Spoolman REST API │
  └────────┬───────────────────────┘
           │ X-Spoolman-Target header
  ┌────────▼───────┐
  │  nginx proxy   │ (/rfid-spools/spoolman/)
  └────────┬───────┘
           │
  ┌────────▼───────┐
  │   Spoolman     │ (external, e.g. 192.168.2.30:7912)
  └────────────────┘
```

---

## Known Issues & Future Work

### To stabilise before merge

- [ ] **Build-time integration for 68-app-rfid-spools:** Currently only deployed
  via `push-rfid-sync.sh`. Needs `pre-scripts/`, `scripts/`, and proper overlay
  integration so it's included in firmware builds.
- [ ] **Klipper restart on deploy:** Step 2 patches `filament_detect.py` at
  runtime, which requires a Klipper restart. For build-time this isn't an issue
  since the patch is applied before first boot.
- [ ] **`logread` availability:** The `openrfid-log` action uses `logread` which
  may not be available on all Buildroot configs. Falls back gracefully (empty
  output), but the UI shows a tip to use SSH instead.

### Potential upstream contributions

- [ ] **OpenRFID: TD + bed temp extraction** — the TigerTag patch (03) could be
  submitted upstream to `suchmememanyskill/OpenRFID`. It's clean, backwards-
  compatible (default `td=0.0`), and follows the TigerTag V1.0 spec.
- [ ] **OpenRFID: `td` in GenericFilament** — adding `td` as a standard field in
  GenericFilament benefits all tag formats, not just TigerTag.

### Future enhancements

- [ ] Auto-sync on tag read (Moonraker websocket subscription for real-time
  updates instead of manual Refresh)
- [ ] Spoolman usage tracking (decrement weight on print completion)
- [ ] Multi-color spool display (RGB_2..RGB_5 from multi-color tags)
- [ ] Custom fields read-back from Spoolman to pre-fill missing RFID data
