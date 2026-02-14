# 25-u1-router-led-events

Installs Klipper Router and adds LED status-event consumption for U1 extended Klipper config.

## What it does

- Installs pinned `klipper-router` from `https://github.com/paxx12/klipper-router` during firmware build:
  - daemon: `/usr/local/sbin/klipper-routerd`
  - reference include: `/usr/local/share/firmware-config/router/includes/router_api.cfg`
- Installs init service:
  - `/etc/init.d/S98klipper-router-instances` (starts/stops additional Klippy instances)
  - `/etc/init.d/S99klipper-router`
- Adds default router runtime config:
  - `/usr/local/share/firmware-config/extended/router/klipper_router.cfg`
  - copied to `/home/lava/printer_data/config/extended/router/klipper_router.cfg` on boot
- Adds default additional-instance layout:
  - `/usr/local/share/firmware-config/extended/router/instances/led/printer.cfg`
  - `/usr/local/share/firmware-config/extended/router/instances/led/klipper/*.cfg`
  - copied to `/home/lava/printer_data/config/extended/router/instances/led/` on boot
- Adds default Klipper router API macro config:
  - `/usr/local/share/firmware-config/extended/klipper/15_router_api.cfg`
- Adds LED status subscription/state config:
  - `/usr/local/share/firmware-config/extended/klipper/16_router_led_event_subscriptions.cfg`
- Adds runtime migration script (`S50router-led-events`) to idempotently patch persisted router API config at:
  - `/home/lava/printer_data/config/extended/klipper/15_router_api.cfg`
- Adds firmware-config integration:
  - `/usr/local/share/firmware-config/functions/25_settings_router.yaml`
  - toggle router mode + basic runtime status visibility

## Why runtime migration is included

`/home/lava/printer_data/config/extended/*` is persistent and not overwritten by default updates. The migration script ensures existing installs receive the reconnect re-subscribe hook.

## Opt-in enablement

Router mode is disabled by default. Enable it in:

`/home/lava/printer_data/config/extended/extended2.cfg`

```ini
[router]
enabled: true
```

When enabled:
- `S98klipper-router-instances` discovers and starts each instance under:
  - `/home/lava/printer_data/config/extended/router/instances/<name>/printer.cfg`
  - sockets: `/home/lava/printer_data/comms/klippy-router-<name>.sock`
- `S99klipper-router` starts router daemon using:
  - `/home/lava/printer_data/config/extended/router/klipper_router.cfg`
  - auto-appends missing `[klippy <name>]` entries for discovered instances into:
    - `/home/lava/printer_data/config/extended/router/klipper_router.runtime.cfg`
