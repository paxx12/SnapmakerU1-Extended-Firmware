---
title: Silent Mode Macros
---

# Silent Mode Macros

Reduce motion noise by lowering speed, acceleration, jerk, fan speed, and XY stepper current with two helper macros: `SILENT_ON` and `SILENT_OFF`. These macros are optional and live in your user configuration, so firmware updates will not overwrite them.

**Available in: Extended firmware (user macros added via `extended/klipper/`)**

## Recommended Macros

Create `extended/klipper/silent-mode.cfg` with the following defaults:

```cfg
[gcode_macro SILENT_ON]
description: Quieter profile for prints (lower speed, accel, jerk, fan, XY current)
gcode:
    # Speed scaling
    M220 S75                      # 75% of slicer/requested speed
    
    # Acceleration
    M204 P6500 T6500              # Lower print/travel acceleration
    
    # Part cooling fan
    M106 S165                     # ~65% PWM (range 0-255)
    
    # Jerk / cornering
    M205 X5 Y5                    # Lower XY jerk to reduce harsh moves
    
    # XY stepper current (Klipper TMC driver current, in amps)
    SET_TMC_CURRENT STEPPER=stepper_x CURRENT=1.0
    SET_TMC_CURRENT STEPPER=stepper_y CURRENT=1.0

[gcode_macro SILENT_OFF]
description: Restore typical performance-oriented values
gcode:
    M220 S100
    M204 P10000 T10000
    M106 S255                     # Full fan speed
    M205 X10 Y10
    SET_TMC_CURRENT STEPPER=stepper_x CURRENT=1.2
    SET_TMC_CURRENT STEPPER=stepper_y CURRENT=1.2
```

Tweak the values as desired. `SET_TMC_CURRENT` values should stay within the motor/driver limits; the above keeps a safe margin from common 1.5A maximums.

## Add the Macros via Fluidd/Mainsail

1. Open Fluidd or Mainsail → **Configuration** → `extended/klipper/`
2. Create `silent-mode.cfg` and paste the macro block above
3. Click **Save**
4. Restart Klipper (or reboot the printer)

## Enable SILENT_ON Automatically

Choose one (or both) behaviors:

**A) Before every print start**

Wrap your existing `PRINT_START` macro so it always calls `SILENT_ON` first:

```cfg
[gcode_macro PRINT_START]
rename_existing: PRINT_START_BASE
gcode:
    SILENT_ON                     # Force quiet profile before each print
    PRINT_START_BASE {rawparams}  # Call your original PRINT_START
```

Place this in `extended/klipper/print-start-silent.cfg` (same folder as above). If you already customized `PRINT_START`, merge the `SILENT_ON` call at the top of your existing macro instead of using `rename_existing`.

**B) On printer boot**

Automatically apply the quiet profile a second after Klipper starts:

```cfg
[delayed_gcode APPLY_SILENT_ON_AT_BOOT]
initial_duration: 1.0
gcode:
    SILENT_ON
```

Add this to `silent-mode.cfg` (or another file in `extended/klipper/`). Remove the block if you no longer want the default applied at startup.

## Usage Notes

- Run `SILENT_ON` or `SILENT_OFF` manually from the console at any time
- If a slicer inserts its own `M204`, `M205`, or `M220` commands during a print, those will override the macro values—remove or adjust them in the slicer if needed
- Lower currents reduce heat and noise but can reduce torque; verify reliable homing and travel moves before unattended prints
- Fan `S` values use the 0–255 Klipper scale; `S165` is roughly 65% duty cycle

## Troubleshooting

- If Klipper refuses to start after adding the file, check for indentation or syntax errors in the `.cfg`
- To revert, delete or rename `silent-mode.cfg` (and any wrapper like `print-start-silent.cfg`) and restart Klipper
- If motion skips after lowering current/acceleration, raise the affected values incrementally
