---
title: OpenRFID Upstream Opportunities
---

# OpenRFID Upstream Opportunities

The [`68-app-rfid-spools`](../../overlays/firmware-extended/68-app-rfid-spools/)
overlay carries several files that live under `/usr/local/share/openrfid/`
and `/usr/local/bin/`. Some of those are pure U1 glue and belong in this
repository forever. Others are extensions or fixes to the OpenRFID
codebase that would be cleaner to land upstream — eliminating monkey-patches
and override files we currently ship as overlays.

This document is a backlog/triage of which pieces could be upstreamed,
in what order, and what the upstream change would need to look like.

## Quick triage

| File (relative to overlay `root/`) | Classification | Notes |
| --- | --- | --- |
| `usr/local/share/openrfid/tag/tigertag/processor.py` | **Upstream candidate** | Adds emoji, message, TD, `bed_temp_min`, `bed_temp_max` parsing — valid TigerTag fields the upstream parser is missing |
| `usr/local/share/openrfid/tag/tigertag/constants.py` | **Drop after upstream PR** | Byte-identical to upstream today; only shipped as a change-tracking pin |
| `usr/local/share/openrfid/filament/generic.py` | **Upstream candidate** | Adds optional `bed_temp_min_c`, `bed_temp_max_c`, `emoji`, `message` fields |
| `usr/local/share/openrfid/extensions/__init__.py` | **Upstream candidate** | Empty placeholder — confirms the overlay is creating a brand-new directory in OpenRFID's tree |
| `usr/local/share/openrfid/extensions/ntag_write.py` | **Upstream candidate** (needs API work) | NTAG215 write support + write HTTP endpoint. Currently a monkey-patch (`GpioEnabledRfidReader.scan` is hot-swapped). Needs an extension/plugin hook upstream first |
| `usr/local/bin/openrfid.py` | **Disappears** if extensions API lands | Only exists to call `extensions.ntag_write.install()` before `runpy.run_path("main.py", ...)` — replace with auto-loader |
| `usr/local/share/openrfid/extended/openrfid_rfid_spools.cfg` | **Maybe ship as example** | Webhook-exporter config (`tag_read` / `tag_parse_error` / `tag_not_present` → POST). Could ship as an example config in OpenRFID |
| `etc/init.d/S99openrfid` | **Investigate** | Overrides the stock init. Diff vs. upstream — if it only changes config path / args, an env var in the stock script would eliminate this override |
| `usr/local/bin/rfid-spools-api.py` | **Stays here** | U1-specific Spoolman bridge / channel state machine / `/spools/api/*` |
| `etc/init.d/S99rfid-spools` | **Stays here** | Init for our own service |
| `etc/nginx/fluidd.d/rfid-spools.conf` | **Stays here** | Nginx glue for `/spools/` |
| `usr/local/share/rfid-spools/html/**` | **Stays here** | UI — entirely ours |

## Recommended order of work

### 1. Cheap parser/field PRs (no API changes needed)

Submit a single PR to the OpenRFID repo containing the additive changes
in:

- `src/tag/tigertag/processor.py`
- `src/filament/generic.py`

Concrete diff (verified against upstream `suchmememanyskill/OpenRFID@main`):

| File | Delta | Summary |
| --- | --- | --- |
| `src/tag/tigertag/processor.py` | +28 lines | Parse the 4-byte emoji + 28-byte custom message at `Constants.OFF_METADATA` (already defined upstream as `48`). Populate `bed_temp_min_c`, `bed_temp_max_c`, `emoji`, `message` on the returned `GenericFilament`. Adds one debug log line. |
| `src/filament/generic.py` | +18 lines | Four new optional kwargs (`bed_temp_min_c`, `bed_temp_max_c`, `emoji`, `message`) with safe defaults (`0.0`, `0.0`, `""`, `""`); matching instance attrs; matching `to_dict()` keys. |

Both changes are **purely additive** — every new constructor argument
has a safe default, no existing callers break, no behavior change for
existing fields. Strong upstream candidate, single PR.

`src/tag/tigertag/constants.py` in the overlay is **byte-identical**
to upstream — we only ship it as a change-tracking pin. Once the PR
lands and we bump our overlay's pinned OpenRFID version, this file
can be removed from the overlay altogether.

Once merged, the overlay drops:

- `root/usr/local/share/openrfid/tag/tigertag/processor.py`
- `root/usr/local/share/openrfid/tag/tigertag/constants.py`
- `root/usr/local/share/openrfid/filament/generic.py`

### 2. Extensions / plugin loader (eliminates the monkey-patch)

Propose an OpenRFID **extensions API**:

- Auto-import every module under an `extensions/` package.
- Each module may expose an `install()` callable, which is invoked
  before the readers are constructed.
- Document a small contract for what `install()` is allowed to do
  (e.g., wrap reader methods, register HTTP handlers under a reserved
  loopback port range, subscribe to lifecycle events).

Once landed, our changes shrink dramatically:

- `extensions/ntag_write.py` becomes a clean first-class plugin (no
  monkey-patching of `GpioEnabledRfidReader.scan`).
- `bin/openrfid.py` is **deleted** — the stock launcher loads our
  plugin automatically.
- `extensions/__init__.py` (empty placeholder) is no longer ours to
  carry.

### 3. Stock-init parity for `S99openrfid`

Diff this overlay's `S99openrfid` against the upstream init to confirm
why we override it. If the only delta is configurability (e.g., choosing
the active `extended2.cfg`), ask upstream for a config-path env var so
we can drop the override entirely.

### 4. Optional: example config in OpenRFID

`openrfid_rfid_spools.cfg` could ship in OpenRFID as a reference example
for "use OpenRFID as a webhook source for an external service". Low
priority — purely cosmetic/discoverability.

## What stays here forever

After all the above lands upstream, this overlay should reduce to:

```
overlays/firmware-extended/68-app-rfid-spools/
├── README.md
├── root/
│   ├── etc/
│   │   ├── init.d/S99rfid-spools
│   │   └── nginx/fluidd.d/rfid-spools.conf
│   └── usr/local/
│       ├── bin/rfid-spools-api.py
│       └── share/rfid-spools/html/...
└── test/push.sh
```

That is the desired end state: this overlay only contains things that
are inherently U1- or firmware-specific (the Spoolman bridge service,
the nginx route, the web UI, and an init script).

## Cross-reference

- Overlay README: [`68-app-rfid-spools/README.md`](../../overlays/firmware-extended/68-app-rfid-spools/README.md)
- TigerTag write path lives in `extensions/ntag_write.py` — see the
  "Write path" section of the overlay README for the protocol details
  that any upstream review will need.
