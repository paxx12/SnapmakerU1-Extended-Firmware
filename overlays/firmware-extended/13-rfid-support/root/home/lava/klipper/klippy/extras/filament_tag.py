# NTAG tag write and erase operations for filament tracking
#
# Copyright (C) 2024 Scott Wiederhold <s.e.wiederhold@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import base64
import logging
from . import fm175xx_reader

FILAMENT_DT_OK = 0
FILAMENT_DT_STATE_IDLE = 0

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
            'FILAMENT_TAG_WRITE',
            self.cmd_FILAMENT_TAG_WRITE,
            desc="Write raw NDEF data to NTAG tag"
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

    def _wait_for_detection(self, channel, timeout=3.0):
        """Wait for filament detection to complete (state returns to IDLE)."""
        deadline = self.reactor.monotonic() + timeout
        while self.reactor.monotonic() < deadline:
            if self.filament_detect._state[channel] == FILAMENT_DT_STATE_IDLE:
                return True
            self.reactor.pause(self.reactor.monotonic() + 0.1)
        return False

    def cmd_FILAMENT_TAG_WRITE(self, gcmd):
        """Write raw NDEF data to NTAG tag.

        Required parameters:
          CHANNEL: RFID channel number (0-3)
          DATA: URL-safe base64 encoded NDEF bytes

        Example:
          FILAMENT_TAG_WRITE CHANNEL=0 DATA=4RBtAAMSElAQYXBwbGljYXRpb24vanNvbg...
        """
        # Check if print is in progress
        print_stats = self.printer.lookup_object('print_stats', None)
        if print_stats and print_stats.get_status(None).get('state') == 'printing':
            raise gcmd.error("Cannot write tag while printing")

        channel = gcmd.get_int('CHANNEL', 0, minval=0, maxval=self.channel_nums-1)
        data_b64 = gcmd.get('DATA')

        if not data_b64:
            raise gcmd.error("DATA parameter is required")

        # Decode URL-safe base64 to bytes
        try:
            # Add padding if stripped
            padding = 4 - len(data_b64) % 4
            if padding != 4:
                data_b64 += '=' * padding
            data_bytes = list(base64.urlsafe_b64decode(data_b64))
        except Exception as e:
            raise gcmd.error(f"Invalid base64 DATA: {e}")

        # Check if tag is present
        error, info = self.filament_detect.get_a_filament_info(channel)
        if error != FILAMENT_DT_OK:
            raise gcmd.error(f"Failed to get tag info for channel {channel}")

        if not info.get('CARD_UID') or len(info.get('CARD_UID', [])) == 0:
            raise gcmd.error(
                f"No RFID tag detected on channel {channel}. "
                "Please insert a tag first.")

        # Verify it's an NTAG tag (not M1)
        card_type = info.get('CARD_TYPE', '')
        if card_type == 'M1':
            raise gcmd.error(
                f"Tag on channel {channel} is M1 type. "
                "This command only supports NTAG tags.")

        # Write to tag
        try:
            result = self.fm175xx_reader.write_ntag_data(channel, data_bytes)
            if result != fm175xx_reader.FM175XX_OK:
                raise gcmd.error(
                    f"Failed to write tag: driver error code {result}")
        except Exception as e:
            logging.exception("Tag write failed")
            raise gcmd.error(f"Failed to write tag: {str(e)}")

        # Verify write by reading back
        self.filament_detect.request_update_filament_info(channel)
        self._wait_for_detection(channel)

        error, verify_info = self.filament_detect.get_a_filament_info(channel)
        if (error == FILAMENT_DT_OK
                and verify_info.get('MAIN_TYPE')
                and verify_info['MAIN_TYPE'] != 'NONE'):
            gcmd.respond_info(
                f"Tag written and verified successfully on channel {channel} | "
                f"Material: {verify_info.get('VENDOR', '')} "
                f"{verify_info.get('MAIN_TYPE', '')} | "
                f"{len(data_bytes)} bytes written")
        else:
            gcmd.respond_info(
                f"Tag written on channel {channel} ({len(data_bytes)} bytes) "
                "but could not verify content. Please read tag to confirm.")

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

        # Verify erase by reading back
        self.filament_detect.request_update_filament_info(channel)
        self._wait_for_detection(channel)

        error, verify_info = self.filament_detect.get_a_filament_info(channel)
        if error == FILAMENT_DT_OK:
            # Tag should now appear empty or have no valid data
            if not verify_info.get('MAIN_TYPE') or verify_info['MAIN_TYPE'] in ('', 'NONE'):
                gcmd.respond_info(f"Tag erased successfully on channel {channel}")
            else:
                gcmd.respond_info(f"Tag erased on channel {channel} (may require manual verification)")
        else:
            gcmd.respond_info(f"Tag erased on channel {channel}")

def load_config(config):
    """Load the filament_tag module."""
    return FilamentTag(config)
