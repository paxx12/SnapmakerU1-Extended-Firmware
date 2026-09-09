# Experimental Anycubic ACE integration

This personal mod adds an experimental Anycubic ACE Pro / ACE 2 Pro path to a
Snapmaker U1. It stays disabled until it is selected in Firmware Config, so a
printer can remain on the stock U1 feeder path when ACE is not in use.

Build it with:

```bash
./dev.sh make build PROFILE=extended-tareku99
```

After flashing the image:

1. Connect one to four ACE units to the U1.
2. Enable Advanced Mode.
3. Open `http://<printer-ip>/firmware-config/`.
4. Under **Settings > Snapmaker Components**, enable **Anycubic ACE
   (experimental)**.

Treat the first run as a clean test installation. The ACE configuration,
persistent state, and frontend layout are created for this implementation.

Firmware Config switches the ACE Klipper modules into place, installs the ACE
include, and restarts Klipper. Disabling the setting restores the stock U1
modules before restarting. The stock path remains available whenever ACE is
disabled.

Enabling ACE also applies the ACE macro layout to both supported web
frontends. Fluidd receives ACE categories, while Mainsail receives ACE macro
groups and dashboard panels. Mainsail must be in **Expert Mode** to display
macro groups; the setup does not change that user preference. If the frontend
database was not ready during enable, use **Firmware Config > Troubleshooting
> Apply ACE macro layout** after opening the frontend.

The runtime supports ACE Pro (JSON/V1) and ACE 2 Pro (protobuf/V2), one to four
devices, stable device ordering, per-device slot state, RFID metadata, feed
assist, load/unload retries, and head-to-ACE/slot mapping. The optional web
service and online updater are deliberately not bundled in this firmware
overlay; activation is managed by Firmware Config instead.

Set `ace_device_count` in the installed `ace.cfg` before enabling the feature
when using more than one ACE. Start with the default of `1` until device
ordering and the physical tube splitters have been verified.

For connector pinouts, wiring, commands, attribution, and the first hardware
test checklist, see the [Anycubic ACE wiring and test guide](../../../../docs/anycubic_ace.md).

The current test setup has successfully completed ACE 2 Pro connection,
RFID/slot detection, loading, unloading, recovery, and a real multi-color U1
print. Additional hardware combinations and repeated recovery cases remain
experimental, so the pull request should remain marked as a draft until those
tests are complete.
