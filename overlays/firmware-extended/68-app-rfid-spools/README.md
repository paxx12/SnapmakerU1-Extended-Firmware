# 68-app-rfid-spools

RFID spool management app for the Snapmaker U1 extended firmware. Receives
OpenRFID scan events, exposes a REST/SSE API, serves a static web UI under
`/spools/`, proxies Spoolman, pushes parsed filament data into Klipper, and
writes TigerTag payloads to NTAG215 tags via the printer's FM175XX readers.

## Architecture

```
┌─────────────┐  webhook   ┌──────────────────────┐  REST   ┌─────────────┐
│  OpenRFID   │───────────>│  rfid-spools backend │────────>│  Spoolman   │
│  scan loop  │            │  (Python, :8093)     │         │  (external) │
└─────────────┘            │  - ChannelStore      │         └─────────────┘
      ▲                    │  - ConfigManager     │
      │ loopback           │  - EventBus (SSE)    │
      │ :8740 /write       │  - Spoolman proxy    │
      │                    │  - TigerTagEncoder   │
      │                    └──────────────────────┘
      │                         ▲    │   │
      │                   GET   │    │   └── PUT /printer/filament_detect/set
      │                   /SSE  │    │       (push parsed data into Klipper)
      │                         │    ▼
      │                         │  /oem/printer_data/config/extended/
      │                         │     rfid-spools.json (persistent)
      │                         │
      │                    ┌──────────────────────┐
      │                    │  rfid-spools UI      │
      │                    │  (static, served by  │
      │                    │   nginx at /spools/) │
      │                    │  - spools page       │
      │                    │  - 4 config pages    │
      │                    │  - tag editor modal  │
      │                    └──────────────────────┘
      │
      └─── OpenRFID daemon (in-process ntag_write extension)
```

- **Backend**: Python `ThreadingHTTPServer` on `127.0.0.1:8093`
- **Frontend**: static HTML/JS/CSS served by nginx at `/spools/`, hash router
- **Persistent config**: `/oem/printer_data/config/extended/rfid-spools.json`
- **Write loopback**: `127.0.0.1:8740` inside the OpenRFID daemon
- **Klipper integration**: NTAG215 read + `filament_detect/set` (added by
  [13-patch-rfid](../13-patch-rfid/))

## Components

### Backend — [root/usr/local/bin/rfid-spools-api.py](root/usr/local/bin/rfid-spools-api.py)

- `ChannelStore` — in-memory state for the 4 channels
- `ConfigManager` — load/save `rfid-spools.json`
- `EventBus` — SSE broadcaster
- Spoolman proxy (status, ping, auto-discover, candidates, filament lookup,
  sync, sync-all, extra-fields registration for TigerTag UID)
- `TigerTagEncoder` — mirrors OpenRFID's `tag/tigertag/constants.py`
  field layout; `tag_id = 0xBC0FCB97`, signature zeroed, timestamp =
  `int(time.time()) − 946684800`
- Reverse-lookup helpers for material / brand / aspect / diameter / unit
  using the bundled OpenRFID JSON registry under
  `/usr/local/share/openrfid/tag/tigertag/database/`

#### Endpoints

| Method | Path                                       | Purpose                                          |
| ------ | ------------------------------------------ | ------------------------------------------------ |
| GET    | `/api/health`                              | health check                                     |
| GET    | `/api/channels`                            | current per-channel state                        |
| GET    | `/api/config`                              | persisted configuration                          |
| PUT    | `/api/config`                              | update + persist configuration                   |
| GET    | `/api/events`                              | SSE stream of channel updates                    |
| POST   | `/api/tag-event`                           | OpenRFID webhook sink (`tag_read`, `tag_parse_error`, `tag_not_present`) |
| POST   | `/api/scan`                                | trigger manual scan                              |
| GET    | `/api/spoolman-status`                     | Spoolman reachability + counts                   |
| GET    | `/api/spoolman-ping`                       | probe a candidate URL                            |
| GET    | `/api/spoolman-discover`                   | auto-discover Spoolman on the network            |
| GET    | `/api/spoolman-candidates`                 | matching spools for a tag                        |
| GET    | `/api/spoolman-filament`                   | filament lookup                                  |
| POST   | `/api/spoolman-sync`                       | sync one channel to Spoolman                     |
| POST   | `/api/spoolman-sync-all`                   | sync every populated channel                     |
| GET    | `/api/spoolman-extra-fields-status`        | check TigerTag UID extra-field registration      |
| POST   | `/api/spoolman-register-extra-fields`      | register the extra fields                        |
| GET    | `/api/tigertag/registry`                   | registry from bundled OpenRFID JSON              |
| POST   | `/api/tigertag/encode-preview`             | 96-byte hex dump (no write)                      |
| POST   | `/api/write`                               | encode TigerTag spec → forward to loopback :8740 |

### OpenRFID overrides

- [extended/openrfid_rfid_spools.cfg](root/usr/local/share/openrfid/extended/openrfid_rfid_spools.cfg)
  — webhook exporter: `tag_read` / `tag_parse_error` / `tag_not_present` →
  `POST /api/tag-event`
- [tag/tigertag/processor.py](root/usr/local/share/openrfid/tag/tigertag/processor.py)
  — adds emoji/message/TD/bed_temp_min/bed_temp_max
- [tag/tigertag/constants.py](root/usr/local/share/openrfid/tag/tigertag/constants.py)
  — keeps constants in sync for the encoder
- [filament/generic.py](root/usr/local/share/openrfid/filament/generic.py)
  — extended generic filament fields

### Write path

- [extensions/ntag_write.py](root/usr/local/share/openrfid/extensions/ntag_write.py)
  — monkey-patches `GpioEnabledRfidReader.scan()` to drain a per-slot pending
  write queue; performs `start_session` (CW on, GPIO toggled) →
  `__reader_a_activate` → page-write loop (NTAG `WRITE = 0xA2`, 4-byte page,
  4-bit ACK with `0x0A` low nibble) → `end_session`. Refuses writes past
  `FM175XX_NTAG215_USER_END_PAGE` (129). Exposes `GET /health` and
  `POST /write {slot, data_b64, start_page}` on `127.0.0.1:8740`,
  blocking on a `threading.Event` until the next scan iteration completes.
- [usr/local/bin/openrfid.py](root/usr/local/bin/openrfid.py) — launcher
  override: identical to the base launcher except it calls
  `extensions.ntag_write.install()` before `runpy.run_path("main.py", ...)`,
  so the monkey-patch is in place before the readers are constructed.
  Failures are logged but never block the daemon.

### Frontend — [root/usr/local/share/rfid-spools/html/](root/usr/local/share/rfid-spools/html/)

- Shell: [index.html](root/usr/local/share/rfid-spools/html/index.html),
  [style.css](root/usr/local/share/rfid-spools/html/style.css),
  [app.js](root/usr/local/share/rfid-spools/html/app.js),
  [router.js](root/usr/local/share/rfid-spools/html/router.js),
  [utils.js](root/usr/local/share/rfid-spools/html/utils.js)
- Pages:
  - [pages/spools.js](root/usr/local/share/rfid-spools/html/pages/spools.js)
    — channel cards, Spoolman sync footer, "Edit" button opens the TigerTag
    editor modal (centered, close on Esc / backdrop). The editor pre-fills
    every field from the cached scan data; values not present in the
    registry surface as `(custom)` options. Diameter pre-fill uses bare
    numbers (`"1.75"`); unit defaults to `"g"`. Color picker, temps/weight
    numeric inputs, emoji + 28-char message input. Write → `POST /api/write`.
  - [pages/config-shared.js](root/usr/local/share/rfid-spools/html/pages/config-shared.js)
  - [pages/config-slots.js](root/usr/local/share/rfid-spools/html/pages/config-slots.js)
  - [pages/config-tag-mapping.js](root/usr/local/share/rfid-spools/html/pages/config-tag-mapping.js)
  - [pages/config-spoolman.js](root/usr/local/share/rfid-spools/html/pages/config-spoolman.js)

### Init / nginx

- [root/etc/init.d/S99rfid-spools](root/etc/init.d/S99rfid-spools) — backend service
- [root/etc/init.d/S99openrfid](root/etc/init.d/S99openrfid) — selects the
  detect config based on `components.rfid.snapmaker` in `extended2.cfg`
- [root/etc/nginx/fluidd.d/rfid-spools.conf](root/etc/nginx/fluidd.d/rfid-spools.conf)
  — serves `/spools/` static files + reverse-proxies `/spools/api/`

### Related Klipper patches — [../13-patch-rfid/patches/](../13-patch-rfid/patches/)

- `01-add-ntag215-support.patch`
- `02-add-ndef-protocol.patch`
- `03-fm175xx-reader-enabled-guard.patch`
- `04-filament-detect-reader-enabled-guard.patch`
- `05-add-filament-detect-set-endpoint.patch`

## Notes on the TigerTag format

- Tags carry an `OFF_SIGNATURE` field (bytes 80–95 of user data). OpenRFID
  does not verify it, so writing as "unsigned" (signature bytes zero)
  round-trips fine through both the printer firmware reader and OpenRFID.
- The TigerTag registry JSON files (`id_material.json`, `id_brand.json`,
  `id_aspect.json`, …) are bundled with OpenRFID under
  `/usr/local/share/openrfid/tag/tigertag/database/`. The backend reuses
  them rather than duplicating.
- `id_diameter.json` labels are bare numbers (`"1.75"`, `"2.85"`);
  `id_measure_unit.json` has unit symbols (`"g"`, `"kg"`, `"mm"`).

## Development workflow

```bash
# Quick push to printer for testing
./overlays/firmware-extended/68-app-rfid-spools/test/push.sh root@<printer-ip>
```

## Pending

- `root/usr/local/share/firmware-config/functions/68_settings_rfid_spools.yaml`
  — enable/disable in firmware-config UI
- `docs/rfid_spools.md` — user-facing documentation
- TigerTag encode/decode unit tests under [test/](test/)
- Polish pass: error handling, loading states, offline indicators
