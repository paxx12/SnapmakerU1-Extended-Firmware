"""RFID Spools Management API — modular package.

The package is organized into focused modules:

  - :mod:`rfid_spools.constants`  — paths, sizes, numeric constants
  - :mod:`rfid_spools.state`      — EventBus, ChannelStore, SyncStateStore
  - :mod:`rfid_spools.config`     — load_config / save_config
  - :mod:`rfid_spools.moonraker`  — Moonraker REST helpers
  - :mod:`rfid_spools.discovery`  — Spoolman discovery (probe + LAN sweep)
  - :mod:`rfid_spools.formatting` — color/date helpers
  - :mod:`rfid_spools.spoolman`   — Spoolman REST client + sync logic
  - :mod:`rfid_spools.tigertag`   — TigerTag registry + 96-byte encoder +
                                    OpenRFID write loopback
  - :mod:`rfid_spools.handler`    — HTTP request handler (routing only)
  - :mod:`rfid_spools.server`     — logging setup, argparse, ``main()``

The CLI entry-point at ``/usr/local/bin/rfid-spools-api.py`` is a tiny
script that simply invokes :func:`rfid_spools.server.main`.
"""
