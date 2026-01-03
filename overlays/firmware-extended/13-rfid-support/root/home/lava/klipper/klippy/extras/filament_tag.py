# NTAG tag write and erase operations for filament tracking
#
# Copyright (C) 2024 Scott Wiederhold <s.e.wiederhold@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import copy
import logging
from . import filament_protocol
from . import filament_protocol_ndef
from . import fm175xx_reader

# Material density defaults (g/cm³) for OpenSpool format
MATERIAL_DENSITIES = {
    'PLA': 1.24,
    'PETG': 1.27,
    'ABS': 1.04,
    'TPU': 1.21,
    'PVA': 1.19,
    'NYLON': 1.14,
    'ASA': 1.07,
    'PC': 1.20
}

FILAMENT_DT_OK = 0

class FilamentTag:
    """Klipper module for writing and erasing NTAG filament tags."""

    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode = self.printer.lookup_object('gcode')
        self.reactor = self.printer.get_reactor()

        # Will be initialized in klippy:ready handler
        self.filament_detect = None
        self.fm175xx_reader = None
        self.channel_nums = 4

        # Register gcode commands
        self.gcode.register_command(
            'FILAMENT_TAG_WRITE_OPENSPOOL',
            self.cmd_FILAMENT_TAG_WRITE_OPENSPOOL,
            desc="Write OpenSpool NDEF data to NTAG tag"
        )
        self.gcode.register_command(
            'FILAMENT_TAG_ERASE',
            self.cmd_FILAMENT_TAG_ERASE,
            desc="Erase NTAG tag"
        )

        # Register ready handler to access filament_detect module
        self.printer.register_event_handler("klippy:ready", self._handle_ready)

    def _handle_ready(self):
        """Initialize module references once Klipper is ready."""
        try:
            self.filament_detect = self.printer.lookup_object('filament_detect')
            self.fm175xx_reader = self.filament_detect._fm175xx_reader
            self.channel_nums = self.filament_detect._channel_nums
        except Exception as e:
            logging.error(f"FilamentTag: Failed to initialize: {e}")
            raise

    def cmd_FILAMENT_TAG_WRITE_OPENSPOOL(self, gcmd):
        """Write complete OpenSpool format to NTAG tag.

        Required parameters:
          CHANNEL: RFID channel number (0-3)
          TYPE: Material type (PLA, PETG, ABS, TPU, PVA, NYLON, ASA, PC)
          BRAND: Filament brand/manufacturer
          COLOR: Primary color as 6-digit hex (e.g., FF0000 for red)

        Optional parameters:
          SUBTYPE: Material subtype (e.g., "Matte", "Silk")
          DIAMETER: Filament diameter in mm (default: 1.75)
          DENSITY: Material density in g/cm³ (defaults from material type)
          ALPHA: Color alpha/transparency as 2-digit hex (default: FF for opaque)
          COLOR2-5: Additional colors for multicolor spools (6-digit hex)
          MIN_TEMP: Minimum extruder temperature (°C)
          MAX_TEMP: Maximum extruder temperature (°C)
          BED_MIN_TEMP: Minimum bed temperature (°C)
          BED_MAX_TEMP: Maximum bed temperature (°C)
          WEIGHT: Initial spool weight in grams

        Example:
          FILAMENT_TAG_WRITE_OPENSPOOL CHANNEL=0 TYPE=PLA BRAND="Generic" COLOR=FF0000 DIAMETER=1.75
        """
        # Check if print is in progress
        print_stats = self.printer.lookup_object('print_stats', None)
        if print_stats and print_stats.get_status(None).get('state') == 'printing':
            raise gcmd.error("Cannot write tag while printing")

        # Parse and validate parameters
        channel = gcmd.get_int('CHANNEL', 0, minval=0, maxval=self.channel_nums-1)
        material_type = gcmd.get('TYPE', 'PLA').upper()
        brand = gcmd.get('BRAND', 'Generic')
        color_str = gcmd.get('COLOR', 'FFFFFF').upper().lstrip('#')
        diameter = gcmd.get_float('DIAMETER', 1.75, minval=1.0, maxval=3.0)

        # Validate color hex
        try:
            color_rgb = int(color_str, 16)
            if len(color_str) != 6:
                raise ValueError()
        except (ValueError, TypeError):
            raise gcmd.error(f"Invalid COLOR '{color_str}', must be 6-digit hex (e.g., FF0000)")

        # Validate material type
        valid_types = list(MATERIAL_DENSITIES.keys())
        if material_type not in valid_types:
            raise gcmd.error(f"Invalid TYPE '{material_type}', valid types: {', '.join(valid_types)}")

        # Optional parameters
        subtype = gcmd.get('SUBTYPE', None)
        density = gcmd.get_float('DENSITY', None, minval=0.1, maxval=5.0)
        if density is None:
            density = MATERIAL_DENSITIES.get(material_type, 1.24)

        # Alpha transparency (00-FF hex)
        alpha_str = gcmd.get('ALPHA', 'FF').upper().lstrip('#')
        try:
            alpha = int(alpha_str, 16)
            if len(alpha_str) != 2 or alpha < 0 or alpha > 255:
                raise ValueError()
        except (ValueError, TypeError):
            raise gcmd.error(f"Invalid ALPHA '{alpha_str}', must be 2-digit hex (00-FF)")

        # Additional colors (COLOR2-5)
        additional_colors = []
        for i in range(2, 6):
            color_param = f'COLOR{i}'
            color_val = gcmd.get(color_param, None)
            if color_val:
                color_val = color_val.upper().lstrip('#')
                try:
                    color_int = int(color_val, 16)
                    if len(color_val) != 6:
                        raise ValueError()
                    additional_colors.append(color_int)
                except (ValueError, TypeError):
                    raise gcmd.error(f"Invalid {color_param} '{color_val}', must be 6-digit hex (e.g., FF0000)")
            else:
                additional_colors.append(0)

        min_temp = gcmd.get_int('MIN_TEMP', None, minval=100, maxval=350)
        max_temp = gcmd.get_int('MAX_TEMP', None, minval=100, maxval=400)

        # Bed temperature - support both legacy BED_TEMP and new BED_MIN_TEMP/BED_MAX_TEMP
        bed_temp = gcmd.get_int('BED_TEMP', None, minval=0, maxval=150)
        bed_min_temp = gcmd.get_int('BED_MIN_TEMP', None, minval=0, maxval=150)
        bed_max_temp = gcmd.get_int('BED_MAX_TEMP', None, minval=0, maxval=150)

        # Backward compatibility: if BED_TEMP is provided and min/max aren't, use it for both
        if bed_temp is not None and bed_min_temp is None and bed_max_temp is None:
            bed_min_temp = bed_temp
            bed_max_temp = bed_temp

        # Weight in grams
        weight = gcmd.get_float('WEIGHT', None, minval=1.0, maxval=10000.0)

        # Check if tag is present
        error, info = self.filament_detect.get_a_filament_info(channel)
        if error != FILAMENT_DT_OK:
            raise gcmd.error(f"Failed to get tag info for channel {channel}")

        if not info.get('CARD_UID') or len(info.get('CARD_UID', [])) == 0:
            raise gcmd.error(f"No RFID tag detected on channel {channel}. Please insert a tag first.")

        # Verify it's an NTAG tag (not M1)
        card_type = info.get('CARD_TYPE', '')
        if card_type == 'M1':
            raise gcmd.error(f"Tag on channel {channel} is M1 type. This command only supports NTAG tags.")

        # Build filament info structure
        new_info = copy.deepcopy(filament_protocol.FILAMENT_INFO_STRUCT)
        new_info['VERSION'] = 1
        new_info['VENDOR'] = brand
        new_info['MANUFACTURER'] = brand
        new_info['MAIN_TYPE'] = material_type
        new_info['SUB_TYPE'] = subtype if subtype else 'Basic'
        new_info['TRAY'] = 0

        # Color
        new_info['RGB_1'] = color_rgb
        new_info['ALPHA'] = alpha

        # Count non-zero colors
        color_count = 1  # RGB_1 always counts
        for color in additional_colors:
            if color != 0:
                color_count += 1
        new_info['COLOR_NUMS'] = color_count

        new_info['RGB_2'] = additional_colors[0]
        new_info['RGB_3'] = additional_colors[1]
        new_info['RGB_4'] = additional_colors[2]
        new_info['RGB_5'] = additional_colors[3]
        new_info['ARGB_COLOR'] = (alpha << 24) | color_rgb

        # Physical properties
        new_info['DIAMETER'] = int(diameter * 100)  # Convert mm to 1/100mm units
        new_info['DENSITY'] = density
        new_info['WEIGHT'] = int(weight) if weight is not None else 0
        new_info['LENGTH'] = 0
        new_info['DRYING_TEMP'] = 0
        new_info['DRYING_TIME'] = 0

        # Temperatures
        if min_temp is not None:
            new_info['HOTEND_MIN_TEMP'] = min_temp
            new_info['FIRST_LAYER_TEMP'] = min_temp
            new_info['OTHER_LAYER_TEMP'] = min_temp
        else:
            new_info['HOTEND_MIN_TEMP'] = 0
            new_info['FIRST_LAYER_TEMP'] = 0
            new_info['OTHER_LAYER_TEMP'] = 0

        if max_temp is not None:
            new_info['HOTEND_MAX_TEMP'] = max_temp
        else:
            new_info['HOTEND_MAX_TEMP'] = 0

        # Bed temperature - store both min and max
        if bed_min_temp is not None:
            new_info['BED_MIN_TEMP'] = bed_min_temp
        if bed_max_temp is not None:
            new_info['BED_MAX_TEMP'] = bed_max_temp
        # Also set BED_TEMP for backward compatibility (use min or max, whichever is available)
        if bed_min_temp is not None or bed_max_temp is not None:
            new_info['BED_TEMP'] = bed_min_temp if bed_min_temp is not None else bed_max_temp
        else:
            new_info['BED_TEMP'] = 0

        new_info['BED_TYPE'] = 0

        # Other fields
        new_info['SKU'] = 0
        new_info['MF_DATE'] = '19700101'
        new_info['RSA_KEY_VERSION'] = 0
        new_info['OFFICIAL'] = True
        new_info['CARD_UID'] = info['CARD_UID']  # Preserve UID
        new_info['CARD_TYPE'] = 'NTAG215'

        # Encode to NDEF format
        error_code, ndef_data = filament_protocol_ndef.ndef_encode(new_info)
        if error_code != filament_protocol.FILAMENT_PROTO_OK:
            raise gcmd.error(f"Failed to encode NDEF data: error code {error_code}")

        if not ndef_data or len(ndef_data) == 0:
            raise gcmd.error("NDEF encoding returned empty data")

        # Write to tag using fm175xx_reader
        try:
            result = self.fm175xx_reader.write_ntag_data(channel, ndef_data)
            if result != fm175xx_reader.FM175XX_OK:
                raise gcmd.error(f"Failed to write tag: driver error code {result}")
        except Exception as e:
            logging.exception("Tag write failed")
            raise gcmd.error(f"Failed to write tag: {str(e)}")

        # Clear the cached info and force a fresh detection
        self.filament_detect.request_clear_filament_info(channel)
        self.reactor.pause(self.reactor.monotonic() + 0.2)

        # Verify write by reading back
        self.filament_detect.request_update_filament_info(channel)
        self.reactor.pause(self.reactor.monotonic() + 0.5)

        error, verify_info = self.filament_detect.get_a_filament_info(channel)
        if error == FILAMENT_DT_OK:
            if (verify_info.get('VENDOR') == brand and verify_info.get('MAIN_TYPE') == material_type):
                # Build complete message as single line
                msg_parts = [f"Tag written and verified successfully on channel {channel}"]

                # Material information
                material_str = f"Material: {brand} {material_type}"
                if subtype:
                    material_str += f" ({subtype})"
                msg_parts.append(material_str)

                # Color information
                color_str_msg = f"Color: #{color_str}"
                if alpha < 0xFF:
                    color_str_msg += f" (alpha: {alpha:02X})"
                msg_parts.append(color_str_msg)

                # Additional colors
                if any(c != 0 for c in additional_colors):
                    extra_colors = [f"#{c:06X}" for c in additional_colors if c != 0]
                    msg_parts.append(f"Additional colors: {', '.join(extra_colors)}")

                # Diameter and density
                msg_parts.append(f"Diameter: {diameter}mm")
                msg_parts.append(f"Density: {density} g/cm³")

                # Temperature information
                if min_temp and max_temp:
                    temp_str = f"Temperatures: {min_temp}-{max_temp}°C (extruder)"
                    if bed_min_temp is not None or bed_max_temp is not None:
                        if bed_min_temp == bed_max_temp:
                            temp_str += f", {bed_min_temp}°C (bed)"
                        else:
                            temp_str += f", {bed_min_temp or 0}-{bed_max_temp or 0}°C (bed)"
                    msg_parts.append(temp_str)

                # Weight information
                if weight is not None:
                    msg_parts.append(f"Initial spool weight: {weight}g")

                # Send as single message with separator
                gcmd.respond_info(" | ".join(msg_parts))
            else:
                gcmd.respond_info("Warning: Tag written but verification mismatch. Please read tag to verify.")
        else:
            gcmd.respond_info("Tag written but could not verify. Please read tag manually.")

    def cmd_FILAMENT_TAG_ERASE(self, gcmd):
        """Erase NTAG tag (clears all user data).

        Required parameters:
          CHANNEL: RFID channel number (0-3)
          CONFIRM: Must be set to 1 to confirm erase operation

        Example:
          FILAMENT_TAG_ERASE CHANNEL=0 CONFIRM=1
        """
        # Check if print is in progress
        print_stats = self.printer.lookup_object('print_stats', None)
        if print_stats and print_stats.get_status(None).get('state') == 'printing':
            raise gcmd.error("Cannot erase tag while printing")

        channel = gcmd.get_int('CHANNEL', 0, minval=0, maxval=self.channel_nums-1)
        confirm = gcmd.get_int('CONFIRM', 0, minval=0, maxval=1)

        if confirm != 1:
            raise gcmd.error("Tag erase requires CONFIRM=1 parameter to proceed")

        # Check if tag is present
        error, info = self.filament_detect.get_a_filament_info(channel)
        if error != FILAMENT_DT_OK:
            raise gcmd.error(f"Failed to get tag info for channel {channel}")

        if not info.get('CARD_UID') or len(info.get('CARD_UID', [])) == 0:
            raise gcmd.error(f"No RFID tag detected on channel {channel}")

        # Verify it's an NTAG tag (not M1)
        card_type = info.get('CARD_TYPE', '')
        if card_type == 'M1':
            raise gcmd.error(f"Tag on channel {channel} is M1 type. Cannot erase M1 tags.")

        # Create minimal empty NDEF message
        # This includes the Capability Container and an empty NDEF TLV
        # CC (page 3): E1 10 6D 00
        # Empty NDEF TLV (page 4): 03 00 FE (TLV with empty message, then terminator)
        empty_ndef = [0xE1, 0x10, 0x6D, 0x00, 0x03, 0x00, 0xFE]

        try:
            result = self.fm175xx_reader.write_ntag_data(channel, empty_ndef)
            if result != fm175xx_reader.FM175XX_OK:
                raise gcmd.error(f"Failed to erase tag: driver error code {result}")
        except Exception as e:
            logging.exception("Tag erase failed")
            raise gcmd.error(f"Failed to erase tag: {str(e)}")

        # Clear the cached info and force a fresh detection
        self.filament_detect.request_clear_filament_info(channel)
        self.reactor.pause(self.reactor.monotonic() + 0.2)

        # Request an update to verify the tag is now empty
        self.filament_detect.request_update_filament_info(channel)
        self.reactor.pause(self.reactor.monotonic() + 0.5)

        error, verify_info = self.filament_detect.get_a_filament_info(channel)
        if error == FILAMENT_DT_OK:
            # Tag should now appear empty or have no valid data
            if not verify_info.get('MAIN_TYPE') or verify_info.get('MAIN_TYPE') == '':
                gcmd.respond_info(f"Tag erased successfully on channel {channel}")
            else:
                gcmd.respond_info(f"Tag erased on channel {channel} (may require manual verification)")
        else:
            gcmd.respond_info(f"Tag erased on channel {channel}")

def load_config(config):
    """Load the filament_tag module."""
    return FilamentTag(config)
