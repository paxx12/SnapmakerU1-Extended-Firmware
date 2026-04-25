---
title: Faulty Toolhead Bypass
---

# Faulty Toolhead Bypass

This firmware adds a Firmware Config recovery option for Snapmaker U1 printers
that hit error `0003-0523-0000-0002` because one toolhead thermistor is faulty.

It is based on Snapmaker's official guide:

- https://wiki.snapmaker.com/en/snapmaker_u1/troubleshooting/bypass_a_faulty_toolhead

## Warning

This bypass is only intended to let the printer boot and keep using the
remaining toolheads until the damaged part is replaced.

- Do not heat or print with the faulty toolhead while the bypass is enabled.
- Disable the bypass again after the repair is complete.

## Configure

1. Enable Advanced Mode on the printer screen.
2. Open `http://<printer-ip>/firmware-config/`.
3. Go to **Settings -> Troubleshooting**.
4. Use the row for each affected toolhead:
   `Faulty Toolhead 1`, `Faulty Toolhead 2`, `Faulty Toolhead 3`, or
   `Faulty Toolhead 4`.
5. Change that row from **Normal** to **Bypass Thermistor**.
5. Firmware Config will restart Klipper automatically.

To undo it after replacing the faulty part, set each affected toolhead row back
to **Normal**.

## What It Changes

For the selected toolhead, the override:

- remaps the extruder temperature `sensor_pin` to `PC5`
- raises the extruder `max_temp` to `999`
- sets the extruder `max_power` to `0.000001` because Klipper rejects `0`
- sets the matching nozzle cooling fan `heater_temp` to `999`
- sets the matching nozzle cooling fan `fan_speed` to `0`
- changes the last `stepped_temp_table` entry from `260, 0.9` to `260, 0`

Toolhead mapping:

- Toolhead 1 -> `[extruder]` and `[heater_fan e0_nozzle_fan]`
- Toolhead 2 -> `[extruder1]` and `[heater_fan e1_nozzle_fan]`
- Toolhead 3 -> `[extruder2]` and `[heater_fan e2_nozzle_fan]`
- Toolhead 4 -> `[extruder3]` and `[heater_fan e3_nozzle_fan]`

## Implementation Note

Inference from the official guide and the stock U1 `printer.cfg`:

- The official guide says to change the temperature sensor pin suffix to `PC5`.
- Stock U1 configs use per-toolhead MCU pin names (`e0:PA2`, `e1:PA2`,
  `e2:PA2`, `e3:PA2`).
- This firmware therefore implements the remap as `e0:PC5`, `e1:PC5`,
  `e2:PC5`, or `e3:PC5` for the selected toolhead.

The active override is installed into:

```text
/oem/printer_data/config/extended/klipper/
```

Filename pattern:

- `faulty_toolhead1.cfg`
- `faulty_toolhead2.cfg`
- `faulty_toolhead3.cfg`
- `faulty_toolhead4.cfg`

Multiple faulty-toolhead overrides can be enabled at the same time if more than
one toolhead is affected.
