from filament import GenericFilament
from reader.scan_result import ScanResult
from tag.mifare_ultralight_tag_processor import MifareUltralightTagProcessor
from tag.tag_types import TagType
from . import constants as Constants
from .registry import get_tigertag_registry
import struct
from datetime import datetime, timezone

class TigerTagProcessor(MifareUltralightTagProcessor):
    def __init__(self, config: dict):
        super().__init__(config)
        self.registry = get_tigertag_registry()

    def process_tag(self, scan_result: ScanResult, data: bytes) -> GenericFilament | None:
        if scan_result.tag_type != TagType.MifareUltralight:
            return None

        if len(data) < Constants.USER_DATA_BYTE_OFFSET + Constants.OFF_TIMESTAMP + 4:
            return None

        user_data = data[Constants.USER_DATA_BYTE_OFFSET:]

        tag_id = struct.unpack_from('>I', user_data, Constants.OFF_TAG_ID)[0]

        if tag_id not in Constants.TIGERTAG_VALID_DATA_IDS:
            return None

        self.logger.debug("TigerTag: Detected format ID 0x%08X (%s)",
                       tag_id, self.registry.version_ids.get(tag_id, "Unknown"))

        return self.__parse_tigertag(scan_result, user_data, tag_id)

    def __parse_tigertag(self, scan_result: ScanResult, user_data: bytes, tag_id: int) -> GenericFilament | None:
        try:
            product_id = struct.unpack_from('>I', user_data, Constants.OFF_PRODUCT_ID)[0]
            material_id = struct.unpack_from('>H', user_data, Constants.OFF_MATERIAL_ID)[0]
            aspect1_id = user_data[Constants.OFF_ASPECT1_ID]
            aspect2_id = user_data[Constants.OFF_ASPECT2_ID]
            type_id = user_data[Constants.OFF_TYPE_ID]
            diameter_id = user_data[Constants.OFF_DIAMETER_ID]
            brand_id = struct.unpack_from('>H', user_data, Constants.OFF_BRAND_ID)[0]

            r = user_data[Constants.OFF_COLOR_RGBA]
            g = user_data[Constants.OFF_COLOR_RGBA + 1]
            b = user_data[Constants.OFF_COLOR_RGBA + 2]
            a = user_data[Constants.OFF_COLOR_RGBA + 3]
            argb_color = (a << 24) | (r << 16) | (g << 8) | b

            weight_bytes = user_data[Constants.OFF_WEIGHT:Constants.OFF_WEIGHT + 3]
            measure_value = (weight_bytes[0] << 16) | (weight_bytes[1] << 8) | weight_bytes[2]
            unit_id = user_data[Constants.OFF_UNIT_ID]

            temp_min = struct.unpack_from('>H', user_data, Constants.OFF_TEMP_MIN)[0]
            temp_max = struct.unpack_from('>H', user_data, Constants.OFF_TEMP_MAX)[0]
            dry_temp = user_data[Constants.OFF_DRY_TEMP]
            dry_time = user_data[Constants.OFF_DRY_TIME]

            bed_temp_min = user_data[Constants.OFF_BED_TEMP_MIN]
            bed_temp_max = user_data[Constants.OFF_BED_TEMP_MAX]

            # TD (Transmission Distance) — 2-byte big-endian uint16, value/10 = mm
            td_raw = 0
            td_mm = 0.0
            if len(user_data) > Constants.OFF_TD + 1:
                td_raw = struct.unpack_from('>H', user_data, Constants.OFF_TD)[0]
                td_mm = td_raw / 10.0

            timestamp_raw = struct.unpack_from('>I', user_data, Constants.OFF_TIMESTAMP)[0]

            # Emoji (4 bytes UTF-8) and Custom Message (28 bytes UTF-8) from OFF_METADATA
            OFF_EMOJI = Constants.OFF_METADATA       # 48
            OFF_MESSAGE = Constants.OFF_METADATA + 4 # 52
            emoji = ""
            message = ""
            if len(user_data) >= Constants.OFF_METADATA + 4:
                try:
                    emoji = user_data[OFF_EMOJI:OFF_EMOJI + 4].rstrip(b'\x00').decode('utf-8', errors='replace')
                except Exception:
                    emoji = ""
            if len(user_data) >= OFF_MESSAGE + 28:
                try:
                    message = user_data[OFF_MESSAGE:OFF_MESSAGE + 28].rstrip(b'\x00').decode('utf-8', errors='replace')
                except Exception:
                    message = ""

            material_label = self.registry.material_ids.get(material_id, f"Unknown({material_id})")
            material_type = self.registry.material_type_ids.get(material_id, material_label)
            filled_type = self.registry.filled_type_ids.get(material_id, "")
            resolved_material_type = material_type if not filled_type else f"{material_type}-{filled_type}"
            brand_name = self.registry.brand_ids.get(brand_id, f"Unknown({brand_id})")
            diameter_mm = self.registry.diameter_ids.get(diameter_id, 1.75)
            aspect1_label = self.registry.aspect_ids.get(aspect1_id, "")
            aspect2_label = self.registry.aspect_ids.get(aspect2_id, "")
            unit_label = self.registry.unit_ids.get(unit_id, "g")

            weight_grams = self.__convert_to_grams(measure_value, unit_id)
            manufacturing_date = self.__timestamp_to_date(timestamp_raw)

            modifiers = []
            for aspect_label in (aspect1_label, aspect2_label):
                if aspect_label and aspect_label not in ("None", "", "-"):
                    modifiers.append(aspect_label)

            self.logger.debug("Found TigerTag filament:")
            self.logger.debug("  Tag ID: 0x%08X (%s)", tag_id, self.registry.version_ids.get(tag_id, "Unknown"))
            self.logger.debug("  Product ID: 0x%08X", product_id)
            self.logger.debug("  Material: %s / %s (ID: %d)", resolved_material_type, material_label, material_id)
            self.logger.debug("  Brand: %s (ID: %d)", brand_name, brand_id)
            self.logger.debug("  Diameter: %.2f mm (ID: %d)", diameter_mm, diameter_id)
            self.logger.debug("  Aspect1: %s, Aspect2: %s", aspect1_label, aspect2_label)
            self.logger.debug("  Color (ARGB): 0x%08X", argb_color)
            self.logger.debug("  Measure: %d %s (%.1f g)", measure_value, unit_label, weight_grams)
            self.logger.debug("  Nozzle Temp: %d-%d °C", temp_min, temp_max)
            self.logger.debug("  Dry: %d °C for %d hours", dry_temp, dry_time)
            self.logger.debug("  Bed Temp: %d-%d °C", bed_temp_min, bed_temp_max)
            self.logger.debug("  TD: raw=%d → %.1f mm", td_raw, td_mm)
            self.logger.debug("  Emoji: %r", emoji)
            self.logger.debug("  Message: %r", message)
            self.logger.debug("  Timestamp: %d (%s)", timestamp_raw, manufacturing_date)

            return GenericFilament(
                source_processor=self.name,
                unique_id=GenericFilament.generate_unique_id(
                    "TigerTag", brand_name, resolved_material_type, argb_color,
                    product_id, timestamp_raw
                ),
                manufacturer=brand_name,
                type=resolved_material_type,
                modifiers=modifiers,
                colors=[argb_color],
                diameter_mm=diameter_mm,
                weight_grams=weight_grams,
                hotend_min_temp_c=float(temp_min),
                hotend_max_temp_c=float(temp_max),
                bed_temp_c=float(bed_temp_max),
                bed_temp_min_c=float(bed_temp_min),
                bed_temp_max_c=float(bed_temp_max),
                drying_temp_c=float(dry_temp),
                drying_time_hours=float(dry_time),
                manufacturing_date=manufacturing_date,
                td=td_mm,
                emoji=emoji,
                message=message,
            )

        except Exception as e:
            self.logger.exception("TigerTag: Failed to parse tag data: %s", e)
            return None

    def __convert_to_grams(self, value: int, unit_id: int) -> float:
        match unit_id:
            case 1 | 21:
                return float(value)
            case 2 | 35:
                return value * 1000.0
            case 10:
                return value / 1000.0
            case _:
                return float(value)

    def __timestamp_to_date(self, timestamp: int) -> str:
        if timestamp == 0:
            return "0001-01-01"
        try:
            unix_ts = timestamp + Constants.TIGERTAG_EPOCH_OFFSET
            dt = datetime.fromtimestamp(unix_ts, tz=timezone.utc)
            return dt.strftime("%Y-%m-%d")
        except (OSError, OverflowError, ValueError):
            return "0001-01-01"
