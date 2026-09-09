# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-PackageHomePage: https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware
# SPDX-FileCopyrightText: Copyright (c) 2026 @paxx12

# The U1 clears /oem/overlay on every full boot.  ACE mode therefore cannot
# rely on the runtime file swap performed by ace_mode_switch.sh surviving a
# reboot.  Re-apply the selected ACE module set before S60klipper imports it.
# This hook is sourced by S60klipper, so keep failures non-fatal: a disabled
# or incomplete ACE installation must not prevent stock Klipper from starting.

if [ "$1" = "start" ]; then
    ACE_CFG="/home/lava/printer_data/config/extended/klipper/ace.cfg"
    ACE_SWITCH="/usr/local/share/firmware-config/tweaks/klipper/ace/ace_mode_switch.sh"
    ACE_EXTRAS="/home/lava/klipper/klippy/extras"
    ACE_KINEMATICS="/home/lava/klipper/klippy/kinematics"

    # ace.cfg is the enable/disable switch. The ACE module validates the
    # persisted topology and uses all_heads for unsupported values; the
    # saved topology must never prevent the ACE runtime from being restored
    # before Klipper imports it.
    if [ -f "$ACE_CFG" ] \
        && [ -f "$ACE_SWITCH" ] \
        && [ -f "$ACE_EXTRAS/filament_feed_ace.py" ] \
        && [ -f "$ACE_KINEMATICS/extruder_ace.py" ] \
        && [ -f "$ACE_EXTRAS/filament_switch_sensor_ace.py" ]; then
        # Avoid touching the overlay when the correct files are already
        # active (for example during an ordinary Klipper restart).
        if ! cmp -s "$ACE_EXTRAS/filament_feed.py" "$ACE_EXTRAS/filament_feed_ace.py" \
            || ! cmp -s "$ACE_KINEMATICS/extruder.py" "$ACE_KINEMATICS/extruder_ace.py" \
            || ! cmp -s "$ACE_EXTRAS/filament_switch_sensor.py" "$ACE_EXTRAS/filament_switch_sensor_ace.py"; then
            echo "[ACE] Restoring ACE runtime files before Klipper start"
            if ! bash "$ACE_SWITCH" ace; then
                echo "[ACE] WARNING: ACE runtime file activation failed; starting Klipper with current files"
            fi
        fi
    fi
fi
