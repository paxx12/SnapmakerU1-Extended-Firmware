"""Tests for ``rfid_spools.formatting``."""

from rfid_spools.formatting import (
    argb_list_to_multi_hex,
    argb_to_color_hex,
    format_datetime_for_spoolman,
)


# ── argb_to_color_hex ────────────────────────────────────────────────────────
class TestArgbToColorHex:
    def test_int_red(self):
        assert argb_to_color_hex(0xFFFF0000) == 'FF0000'

    def test_int_drops_alpha(self):
        assert argb_to_color_hex(0x00ABCDEF) == 'ABCDEF'

    def test_int_zero(self):
        assert argb_to_color_hex(0) == '000000'

    def test_list_takes_first(self):
        assert argb_to_color_hex([0xFF00FF00, 0xFF0000FF]) == '00FF00'

    def test_string_with_hash(self):
        assert argb_to_color_hex('#abcdef') == 'ABCDEF'

    def test_string_8_chars_drops_alpha(self):
        assert argb_to_color_hex('FFABCDEF') == 'ABCDEF'

    def test_string_wrong_length(self):
        assert argb_to_color_hex('AB') is None

    def test_none(self):
        assert argb_to_color_hex(None) is None

    def test_empty_list(self):
        assert argb_to_color_hex([]) is None


# ── argb_list_to_multi_hex ───────────────────────────────────────────────────
class TestArgbListToMultiHex:
    def test_two_colors(self):
        result = argb_list_to_multi_hex([0xFFFF0000, 0xFF00FF00])
        assert result == 'FF0000,00FF00'

    def test_three_colors(self):
        result = argb_list_to_multi_hex([0xFFFF0000, 0xFF00FF00, 0xFF0000FF])
        assert result == 'FF0000,00FF00,0000FF'

    def test_single_color_returns_none(self):
        # multi_color_hexes only applies when there are >= 2 colors
        assert argb_list_to_multi_hex([0xFFFF0000]) is None

    def test_empty_list(self):
        assert argb_list_to_multi_hex([]) is None

    def test_not_a_list(self):
        assert argb_list_to_multi_hex('FF0000') is None
        assert argb_list_to_multi_hex(None) is None

    def test_mixed_types_skips_non_int(self):
        # Strings inside the list are silently dropped
        result = argb_list_to_multi_hex([0xFFFF0000, 'oops', 0xFF0000FF])
        assert result == 'FF0000,0000FF'

    def test_only_one_int_after_filter_returns_none(self):
        result = argb_list_to_multi_hex([0xFFFF0000, 'oops'])
        assert result is None


# ── format_datetime_for_spoolman ─────────────────────────────────────────────
class TestFormatDatetime:
    def test_yyyymmdd(self):
        assert format_datetime_for_spoolman('20240315') == '2024-03-15T00:00:00'

    def test_iso_date(self):
        assert format_datetime_for_spoolman('2024-03-15') == '2024-03-15T00:00:00'

    def test_iso_datetime_truncated_to_seconds(self):
        assert format_datetime_for_spoolman('2024-03-15T10:30:45.123Z') == '2024-03-15T10:30:45'

    def test_none_returns_none(self):
        assert format_datetime_for_spoolman(None) is None

    def test_empty_string(self):
        assert format_datetime_for_spoolman('') is None

    def test_sentinel_19700101(self):
        assert format_datetime_for_spoolman('19700101') is None

    def test_sentinel_zero(self):
        assert format_datetime_for_spoolman('0') is None

    def test_sentinel_none_string(self):
        assert format_datetime_for_spoolman('NONE') is None

    def test_sentinel_min_iso(self):
        assert format_datetime_for_spoolman('0001-01-01') is None

    def test_unrecognized_format(self):
        assert format_datetime_for_spoolman('not a date') is None

    def test_strips_whitespace(self):
        assert format_datetime_for_spoolman('  20240315  ') == '2024-03-15T00:00:00'
