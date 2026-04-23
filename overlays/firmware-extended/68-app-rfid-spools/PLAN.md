# RFID Spool Management — Implementation Plan

## Architecture (current)

```
┌─────────────┐  webhook   ┌──────────────────────┐  REST   ┌─────────────┐
│  OpenRFID   │───────────>│  rfid-spools backend │────────>│  Spoolman   │
│  scan loop  │            │  (Python, :8093)     │         │  (external) │
└─────────────┘            │  - ChannelStore      │         └─────────────┘
                           │  - ConfigManager     │
                           │  - EventBus (SSE)    │
                           │  - Spoolman proxy    │
                           └──────────────────────┘
                                ▲    │   │   │
                          GET   │    │   │   └── PUT /printer/filament_detect/set
                          /SSE  │    │   │       (push parsed data into Klipper)
                                │    │   ▼
                                │    │  /oem/printer_data/config/extended/
                                │    │     rfid-spools.json (persistent)
                                │    ▼
                           ┌──────────────────────┐
                           │  rfid-spools UI      │
                           │  (static, served by  │
                           │   nginx at /spools/) │
                           │  - spools page       │
                           │  - 4 config pages    │
                           └──────────────────────┘
```

- **Overlay**: [overlays/firmware-extended/68-app-rfid-spools/](.)
- **Backend**: Python `ThreadingHTTPServer` on `127.0.0.1:8093` — webhook receiver, REST API, SSE event stream, Spoolman proxy
- **Frontend**: Static HTML/JS/CSS served via nginx at `/spools/`, hash-based router
- **Persistent config**: `/oem/printer_data/config/extended/rfid-spools.json`
- **Klipper integration**: NTAG215 read + `filament_detect/set` endpoint (added by [13-patch-rfid](../13-patch-rfid/))

---

## Phase 1: Foundation — Basic Spool Display ✅ Done

- [root/etc/init.d/S99rfid-spools](root/etc/init.d/S99rfid-spools), [root/etc/nginx/fluidd.d/rfid-spools.conf](root/etc/nginx/fluidd.d/rfid-spools.conf)
- [root/usr/local/bin/rfid-spools-api.py](root/usr/local/bin/rfid-spools-api.py) — threaded HTTP server, channel store, health/channels endpoints
- HTML/JS/CSS shell + [test/push.sh](test/push.sh) for fast iteration

## Phase 2: Full Tag Display + Tag Type Recognition ✅ Done

- OpenRFID webhook exporter [openrfid_rfid_spools.cfg](root/usr/local/share/openrfid/extended/openrfid_rfid_spools.cfg) → `tag_read` / `tag_parse_error` / `tag_not_present` → `POST /api/tag-event`
- In-tree overrides of bundled openrfid files: [tag/tigertag/processor.py](root/usr/local/share/openrfid/tag/tigertag/processor.py) (adds emoji/message/TD/bed_temp_min/bed_temp_max), [filament/generic.py](root/usr/local/share/openrfid/filament/generic.py)
- Frontend renders source_processor badge + all parsed fields per channel

## Phase 3: Shared Model & Configuration Panel ✅ Done

- Backend: `ChannelStore`, `ConfigManager`, `GET/PUT /api/config`, persisted to `/oem/printer_data/config/extended/rfid-spools.json`
- Multi-page config UI with hash router ([router.js](root/usr/local/share/rfid-spools/html/router.js)):
  - [pages/config-shared.js](root/usr/local/share/rfid-spools/html/pages/config-shared.js)
  - [pages/config-slots.js](root/usr/local/share/rfid-spools/html/pages/config-slots.js)
  - [pages/config-tag-mapping.js](root/usr/local/share/rfid-spools/html/pages/config-tag-mapping.js)
  - [pages/config-spoolman.js](root/usr/local/share/rfid-spools/html/pages/config-spoolman.js)
- Push-to-printer state via Klipper `filament_detect/set` ([13-patch-rfid/patches/05](../13-patch-rfid/patches/05-add-filament-detect-set-endpoint.patch))

## Phase 4: Spoolman Integration ✅ Done

- Backend Spoolman proxy endpoints: `/api/spoolman-status`, `/api/spoolman-ping`, `/api/spoolman-discover`, `/api/spoolman-candidates`, `/api/spoolman-filament`, `/api/spoolman-sync`, `/api/spoolman-sync-all`, `/api/spoolman-extra-fields-status`, `/api/spoolman-register-extra-fields`
- Auto-discovery + manual URL config in `config-spoolman.js`
- Per-channel sync footer in [pages/spools.js](root/usr/local/share/rfid-spools/html/pages/spools.js): name + density edit, sync to existing or create-new, link-back to Spoolman web UI
- Spoolman extra-field registration for TigerTag UID
- SSE event stream at `/api/events` for live channel updates

---

## Phase 5: Tag Writing (TigerTag → NTAG215)

**Goal**: Write 96-byte TigerTag payloads to NTAG215 user pages via the printer's FM175XX readers, with an in-app editor and a "write from Spoolman spool" flow.

### Architecture

The write path lives **inside the OpenRFID daemon** (which already owns SPI),
not in Klipper. This keeps a single SPI client and avoids any service
stop/start dance. There are two pieces:

1. **In-process extension** ([extensions/ntag_write.py](root/usr/local/share/openrfid/extensions/ntag_write.py))
   monkey-patches `GpioEnabledRfidReader.scan()` to drain a per-slot pending
   write queue. When a write is enqueued, the next iteration of OpenRFID's
   normal scan loop performs `start_session` (CW on, GPIO toggled) →
   `__reader_a_activate` → page-write loop (NTAG `WRITE = 0xA2`,
   4-byte page, 4-bit ACK with `0x0A` low-nibble) → `end_session` (CW off).
2. **Loopback HTTP server** on `127.0.0.1:8740` exposes
   `POST /write {slot, data_b64, start_page}` and blocks on a
   `threading.Event` until the scan loop picks the write up.
3. The launcher [openrfid.py](root/usr/local/bin/openrfid.py) (overridden by
   this overlay) installs the extension before `runpy.run_path("main.py", ...)`
   so the monkey-patch is in place before the readers are constructed.

The backend `POST /api/write` now forwards the encoded TigerTag payload to the
loopback endpoint and returns a normalized `{state: success|error, ...}`.

### Findings that shape this phase

- NTAG215 *read* support already exists ([13-patch-rfid/patches/01](../13-patch-rfid/patches/01-add-ntag215-support.patch)). NTAG *write* is exposed solely via OpenRFID — no Klipper changes required.
- TigerTag tags carry an `OFF_SIGNATURE` field (bytes 80–95 of user data) but the OpenRFID parser does not verify it. Writing as "unsigned" (signature bytes zero) round-trips fine through both the printer firmware reader and OpenRFID.
- The TigerTag registry JSON files (`id_material.json`, `id_brand.json`, `id_aspect.json`, …) are bundled with openrfid under `/usr/local/share/openrfid/tag/tigertag/database/`. Backend reuses them rather than duplicating.
- `id_diameter.json` labels are bare numbers (`"1.75"`, `"2.85"`); `id_measure_unit.json` has unit symbols (`"g"`, `"kg"`, `"mm"`). The frontend pre-fill normalizes accordingly.
- Newly-written tags use `TAG_ID = 0xBC0FCB97` (the newer of the two values in `TIGERTAG_VALID_DATA_IDS`); timestamp = `int(time.time()) − TIGERTAG_EPOCH_OFFSET (946684800)`.

### Work items

1. **OpenRFID write extension** ([extensions/ntag_write.py](root/usr/local/share/openrfid/extensions/ntag_write.py))
   - Monkey-patches `GpioEnabledRfidReader` to register itself by `slot` and to drain a pending-write queue before each scan
   - Implements `__reader_a_ntag_page_write(page, data4)` (NTAG `WRITE = 0xA2`, 4-byte page, 4-bit ACK)
   - Loop covers pages `[start_page, start_page + ceil(len/4) − 1]`, refusing writes past `FM175XX_NTAG215_USER_END_PAGE` (129)
   - Threaded `http.server.ThreadingHTTPServer` on `127.0.0.1:8740` exposes `GET /health` and `POST /write`

2. **Launcher override** ([usr/local/bin/openrfid.py](root/usr/local/bin/openrfid.py))
   - Identical to the base launcher except it imports and calls `extensions.ntag_write.install()` before running `main.py`. Failures are logged but never block the daemon.

3. **Backend** ([rfid-spools-api.py](root/usr/local/bin/rfid-spools-api.py))
   - `TigerTagEncoder` class — mirrors the field layout from [openrfid tigertag/constants.py](https://github.com/suchmememanyskill/openrfid/blob/main/src/tag/tigertag/constants.py): `OFF_TAG_ID..OFF_SIGNATURE`
   - `encode(spec) -> bytes(96)`: `tag_id=0xBC0FCB97`, signature zeroed
   - Reverse-lookup helpers using the bundled JSON registry (label → id) for material, brand, aspect, diameter, unit
   - Endpoints:
     - `GET  /api/tigertag/registry` → registry from bundled JSON
     - `POST /api/tigertag/encode-preview` → 96-byte hex dump (no write)
     - `POST /api/write` → `{channel, spec}` → encode → POST to `127.0.0.1:8740/write` → return normalized result
   - Spoolman → TigerTag mapper reuses the Spoolman proxy already in place

4. **Frontend** ([pages/spools.js](root/usr/local/share/rfid-spools/html/pages/spools.js), [style.css](root/usr/local/share/rfid-spools/html/style.css))
   - "Edit" button on each channel card opens a centered modal dialog (overlay + close-on-Esc + close-on-backdrop)
   - Editor pre-fills *all* fields from the cached scan data; values not present in the registry surface as `(custom)` options so the user always sees the current value
   - Diameter pre-fill uses bare numbers (`"1.75"`); Unit defaults to `"g"`
   - Color picker, temps/weight numeric inputs, emoji + 28-char message input
   - Write button → POSTs to `/api/write` → success closes the modal and refreshes the channel; failure stays open with the error message


---

## Phase 6: Polish, Firmware Config & Documentation

- Add `root/usr/local/share/firmware-config/functions/68_settings_rfid_spools.yaml` — enable/disable in firmware config UI
- Documentation `docs/rfid_spools.md`
- TigerTag encode/decode unit tests under [test/](test/)
- Polish: error handling, loading states, offline indicators

---

## Development Workflow

```bash
# Quick push to printer for testing
./overlays/firmware-extended/68-app-rfid-spools/test/push.sh root@<printer-ip>
```
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
