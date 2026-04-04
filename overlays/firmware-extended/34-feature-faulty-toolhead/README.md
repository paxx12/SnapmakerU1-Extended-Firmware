# Faulty Toolhead Bypass

This overlay adds a Firmware Config setting that applies Snapmaker's temporary
workaround for error `0003-0523-0000-0002` when one toolhead thermistor is
damaged and prevents the printer from booting normally.

Each toolhead setting installs its own Klipper override independently.
Each override:

- remaps the affected extruder temperature sensor pin to `PC5`
- raises the affected extruder `max_temp` to `999`
- sets the affected extruder `max_power` to `0.000001`
- sets the matching nozzle cooling fan `heater_temp` to `999`
- sets the matching nozzle cooling fan `fan_speed` to `0`
- changes the last `stepped_temp_table` entry to `260, 0`

Toolhead mapping:

- Toolhead 1 -> `[extruder]` and `[heater_fan e0_nozzle_fan]`
- Toolhead 2 -> `[extruder1]` and `[heater_fan e1_nozzle_fan]`
- Toolhead 3 -> `[extruder2]` and `[heater_fan e2_nozzle_fan]`
- Toolhead 4 -> `[extruder3]` and `[heater_fan e3_nozzle_fan]`

Source:

- Snapmaker Wiki: https://wiki.snapmaker.com/en/snapmaker_u1/troubleshooting/bypass_a_faulty_toolhead

Inference from the stock U1 `printer.cfg`:

- The official guide says to change the sensor pin suffix to `PC5`.
- Stock U1 config uses per-toolhead MCU prefixes (`e0:PA2`, `e1:PA2`,
  `e2:PA2`, `e3:PA2`), so this overlay implements that as `e0:PC5`,
  `e1:PC5`, `e2:PC5`, and `e3:PC5`.

This is a temporary recovery aid so the remaining toolheads can be used until
the faulty part is replaced. Enable it only for the affected toolheads and
disable it again after repair.
