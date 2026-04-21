# RFID Spool Management — Implementation Plan

## Architecture Overview

```
┌─────────────┐   webhook    ┌──────────────────┐   REST    ┌─────────────┐
│  OpenRFID   │─────────────>│  rfid-spools     │─────────>│  Spoolman   │
│  (reader)   │              │  backend (Python) │          │  (external) │
└─────────────┘              └──────────────────┘          └─────────────┘
                                    │  ▲
                              nginx │  │ API
                                    ▼  │
                             ┌──────────────────┐
                             │  rfid-spools     │
                             │  frontend (HTML) │
                             └──────────────────┘
                                    │
                                    ▼ (via Moonraker)
                             ┌──────────────────┐
                             │  Klipper/         │
                             │  filament_detect  │
                             └──────────────────┘
```

- **Overlay**: `overlays/firmware-extended/68-app-rfid-spools/`
- **Backend**: Python HTTP server on `127.0.0.1:8093` receiving OpenRFID webhooks + serving API
- **Frontend**: Static HTML/JS/CSS served via nginx at `/spools/`
- **Config**: Persistent in `/oem/printer_data/config/extended/rfid-spools.json`

---

## Phase 1: Foundation — Basic Spool Display (4 channels)

**Goal**: Create the overlay, serve a page showing current filament state from all 4 RFID slots.

**Files created**:
- `68-app-rfid-spools/root/etc/init.d/S99rfid-spools` — init.d service
- `68-app-rfid-spools/root/etc/nginx/fluidd.d/rfid-spools.conf` — nginx routing
- `68-app-rfid-spools/root/usr/local/bin/rfid-spools-api.py` — Python backend (minimal: health endpoint + webhook receiver)
- `68-app-rfid-spools/root/usr/local/share/rfid-spools/html/index.html` — Main page structure
- `68-app-rfid-spools/root/usr/local/share/rfid-spools/html/app.js` — JS: fetches `filament_detect` from Moonraker, renders 4 channel cards
- `68-app-rfid-spools/root/usr/local/share/rfid-spools/html/style.css` — Basic styling
- `68-app-rfid-spools/test/push.sh` — Deploy script: `scp` overlay root to printer + restart service

**How it works**:
- Frontend calls Moonraker `GET /printer/objects/query?filament_detect` to get basic data per channel
- Displays: vendor, material type, subtype, color swatch, temps, UID
- Backend receives OpenRFID webhooks and stores full `GenericFilament` data per channel in memory

---

## Phase 2: Full Tag Display with Tag Type Recognition

**Goal**: Show all OpenRFID-parsed fields and the recognized tag type.

**Changes**:
- Add webhook exporter config to OpenRFID that posts **full** `GenericFilament` + `scan` data to the backend (`POST http://localhost:8093/api/tag-event`)
- `68-app-rfid-spools/root/usr/local/share/openrfid/extended/openrfid_rfid_spools.cfg` — webhook exporter config
- Backend stores full tag data per channel (source_processor, UID, manufacturer, type, modifiers, colors, weight, diameter, TD, drying info, manufacturing date)
- Frontend API: `GET /spools/api/channels` → returns enriched channel data
- Frontend displays: tag type badge (OpenSpool/TigerTag/Snapmaker/etc.), all parsed fields, color swatches, manual entry indicator

---

## Phase 3: Shared Model & Configuration Panel

**Goal**: Define a unified model that consolidates different tag formats, with configurable field mappings.

**Shared model fields** (minimalistic):
```
vendor, material_type, material_subtype, name, colors[],
hotend_min_temp, hotend_max_temp, bed_temp_min, bed_temp_max,
weight_grams, diameter_mm, td, drying_temp, drying_time,
card_uid, tag_type, extra{}
```

**Changes**:
- Backend: `SharedModel` class with mapping logic per tag type
- Backend: `GET/PUT /spools/api/config` — persistent config endpoints
- Config file: `/oem/printer_data/config/extended/rfid-spools.json`
- Frontend: Configuration panel (settings modal/page):
  - TigerTag aspect IDs → subtype mapping (e.g., comma-separated)
  - TigerTag comment → name mapping
  - Custom field mappings per tag type
- Config survives reboots/upgrades (stored under `/oem/`)

---

## Phase 4: Spoolman Integration

**Goal**: Connect to Spoolman for spool management.

**Changes**:
- Backend: Spoolman proxy endpoints (avoids CORS):
  - `GET /spools/api/spoolman/info` — vendor/filament/spool counts
  - `GET /spools/api/spoolman/spools` — list spools with search
  - `POST /spools/api/spoolman/import` — import tag → create Spoolman spool
  - `GET /spools/api/spoolman/vendors`, `/filaments`
- Backend: Spoolman URL auto-discovery (try common ports/hostnames) + manual config
- Frontend:
  - Spoolman connection setup (auto-discover + manual URL input)
  - Dashboard bar: "42 spools | 15 filaments | 8 vendors" with clickthrough links
  - Per-channel "Import to Spoolman" button
  - Spool picker dialog (search by name/material/vendor, select existing spool)
- Config: Spoolman URL stored in rfid-spools.json

---

## Phase 5: Tag Writing (TigerTag)

**Goal**: Write TigerTag format to NTAG215 tags via the printer's built-in FM175XX readers.

**Changes**:
- New Klipper patch: `06-add-ntag215-write-support.patch` in `13-patch-rfid/patches/`
  - Adds `__reader_a_ntag215_write_page()` and `__reader_a_ntag215_write_all_data()` to `fm175xx_reader.py`
  - Adds webhook endpoint `filament_detect/write` to `filament_detect.py`
- Backend:
  - `POST /spools/api/write` — accepts channel + TigerTag data, calls Klipper write endpoint
  - TigerTag binary encoder (reverse of the parser: struct.pack with registry IDs)
  - TigerTag registry data bundled (material/brand/aspect ID JSON files from TigerTag API)
- Frontend:
  - Per-channel "Write Tag" button (for NTAG215 tags)
  - TigerTag editor form: material, brand, colors, temps, weight, aspects, comment
  - "Write from Spoolman" flow: select Spoolman spool → map to TigerTag → write
  - Write progress/verification feedback

---

## Phase 6: Polish, Firmware Config & Documentation

**Goal**: Production readiness.

**Changes**:
- `68-app-rfid-spools/root/usr/local/share/firmware-config/functions/68_settings_rfid_spools.yaml` — enable/disable in firmware config UI
- Error handling, loading states, offline indicators
- Documentation in `docs/rfid_spools.md`
- Integration with existing firmware config YAML for enable/disable toggle
- Test suite for TigerTag encoding/decoding

---

## Development Workflow

Each phase produces a working system testable via:
```bash
# Quick push to printer for testing (the push.sh script)
./overlays/firmware-extended/68-app-rfid-spools/test/push.sh root@<printer-ip>
```
