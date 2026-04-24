"""Tests for ``rfid_spools.tigertag`` — encoder, message bytes, color parser."""

from unittest.mock import patch

import pytest

from rfid_spools import tigertag
from rfid_spools.constants import TIGERTAG_TAG_ID, TIGERTAG_USER_DATA_LEN
from rfid_spools.tigertag import (
    _hex_to_rgba,
    _utf8_message_bytes,
    encode_tigertag,
)


# ── _utf8_message_bytes ──────────────────────────────────────────────────────
class TestUtf8MessageBytes:
    def test_empty_returns_zeros(self):
        assert _utf8_message_bytes('', max_bytes=10) == b'\x00' * 10

    def test_none_returns_zeros(self):
        assert _utf8_message_bytes(None, max_bytes=10) == b'\x00' * 10

    def test_pads_short(self):
        out = _utf8_message_bytes('hi', max_bytes=10)
        assert out == b'hi' + b'\x00' * 8

    def test_truncates_at_codepoint_boundary(self):
        # 'aé' is b'a\xc3\xa9' (3 bytes). max_bytes=2 must NOT split the 'é'.
        # The function should back up to the start of the codepoint and pad.
        out = _utf8_message_bytes('aé', max_bytes=2)
        assert len(out) == 2
        end = out.index(b'\x00') if b'\x00' in out else len(out)
        out[:end].decode('utf-8')  # raises if truncated mid-codepoint

    def test_exact_fit_no_padding(self):
        out = _utf8_message_bytes('hello', max_bytes=5)
        assert out == b'hello'

    def test_default_28_bytes(self):
        assert len(_utf8_message_bytes('x')) == 28


# ── _hex_to_rgba ─────────────────────────────────────────────────────────────
class TestHexToRgba:
    def test_6char_with_hash(self):
        assert _hex_to_rgba('#FF8800') == (0xFF, 0x88, 0x00, 0xFF)

    def test_6char_without_hash(self):
        assert _hex_to_rgba('FF8800') == (0xFF, 0x88, 0x00, 0xFF)

    def test_8char_includes_alpha(self):
        assert _hex_to_rgba('FF880080') == (0xFF, 0x88, 0x00, 0x80)

    def test_lowercase(self):
        assert _hex_to_rgba('ff8800') == (0xFF, 0x88, 0x00, 0xFF)

    def test_list_3(self):
        assert _hex_to_rgba([10, 20, 30]) == (10, 20, 30, 0xFF)

    def test_list_4(self):
        assert _hex_to_rgba([10, 20, 30, 40]) == (10, 20, 30, 40)

    def test_garbage_returns_default(self):
        assert _hex_to_rgba('XYZ') == (0, 0, 0, 0xFF)

    def test_none_returns_default(self):
        assert _hex_to_rgba(None) == (0, 0, 0, 0xFF)


# ── encode_tigertag ──────────────────────────────────────────────────────────
_FAKE_REGISTRY = {
    'materials': [], 'brands': [], 'aspects': [], 'diameters': [],
    'units': [], 'types': [],
    '_idx_material': {'pla': 1, 'pla basic': 2},
    '_idx_brand': {'bambu': 5},
    '_idx_aspect': {'matte': 7},
    '_idx_diameter': {'1.75mm': 175},
    '_idx_unit': {'g': 1},
    '_idx_type': {'standard': 3},
}


@pytest.fixture
def fake_registry():
    """Stub out the disk-backed TigerTag DB loader."""
    with patch.object(tigertag, 'load_tigertag_registry', return_value=_FAKE_REGISTRY):
        yield


class TestEncodeTigertag:
    def test_returns_correct_length(self, fake_registry):
        out = encode_tigertag({})
        assert len(out) == TIGERTAG_USER_DATA_LEN
        assert TIGERTAG_USER_DATA_LEN == 96

    def test_magic_header_at_offset_0(self, fake_registry):
        out = encode_tigertag({})
        assert out[0:4] == TIGERTAG_TAG_ID.to_bytes(4, 'big')
        assert TIGERTAG_TAG_ID == 0xBC0FCB97

    def test_product_id_big_endian(self, fake_registry):
        out = encode_tigertag({'product_id': 0xDEADBEEF})
        assert out[4:8] == b'\xde\xad\xbe\xef'

    def test_material_id_resolved_by_label(self, fake_registry):
        out = encode_tigertag({'material': 'PLA Basic'})
        assert int.from_bytes(out[8:10], 'big') == 2

    def test_material_id_passthrough_int(self, fake_registry):
        out = encode_tigertag({'material': 99})
        assert int.from_bytes(out[8:10], 'big') == 99

    def test_aspect_ids_at_10_and_11(self, fake_registry):
        out = encode_tigertag({'aspect_1': 'Matte', 'aspect_2': 9})
        assert out[10] == 7
        assert out[11] == 9

    def test_brand_id_big_endian(self, fake_registry):
        out = encode_tigertag({'brand': 'Bambu'})
        assert int.from_bytes(out[14:16], 'big') == 5

    def test_color_rgba_at_16_through_19(self, fake_registry):
        out = encode_tigertag({'color': '#FF8800'})
        assert out[16] == 0xFF
        assert out[17] == 0x88
        assert out[18] == 0x00
        assert out[19] == 0xFF  # default alpha

    def test_weight_3byte_be(self, fake_registry):
        out = encode_tigertag({'weight_g': 1000})
        weight = (out[20] << 16) | (out[21] << 8) | out[22]
        assert weight == 1000

    def test_temps_at_24_28(self, fake_registry):
        out = encode_tigertag({'temp_min_c': 200, 'temp_max_c': 230})
        assert int.from_bytes(out[24:26], 'big') == 200
        assert int.from_bytes(out[26:28], 'big') == 230

    def test_dry_and_bed_temps_single_byte(self, fake_registry):
        out = encode_tigertag({
            'dry_temp_c': 45, 'dry_time_h': 8,
            'bed_temp_min_c': 55, 'bed_temp_max_c': 65,
        })
        assert out[28] == 45
        assert out[29] == 8
        assert out[30] == 55
        assert out[31] == 65

    def test_td_mm_encoded_as_tenths(self, fake_registry):
        out = encode_tigertag({'td_mm': 1.5})
        assert int.from_bytes(out[44:46], 'big') == 15

    def test_message_at_offset_48(self, fake_registry):
        out = encode_tigertag({'message': 'hello'})
        assert out[48:53] == b'hello'
        # Bytes 53..75 (28-byte message slot starting at 48) are zero pads
        assert out[53:48 + 28] == b'\x00' * (28 - 5)

    def test_signature_zeroed(self, fake_registry):
        out = encode_tigertag({})
        assert out[80:96] == b'\x00' * 16

    def test_clamps_oversized_values(self, fake_registry):
        out = encode_tigertag({
            'weight_g': 0xFFFFFFFF,        # too big for 3 bytes
            'temp_min_c': 0xFFFFFF,         # too big for 2 bytes
            'dry_temp_c': 9999,             # too big for 1 byte
        })
        assert (out[20], out[21], out[22]) == (0xFF, 0xFF, 0xFF)
        assert int.from_bytes(out[24:26], 'big') == 0xFFFF
        assert out[28] == 0xFF

    def test_empty_spec_does_not_crash(self, fake_registry):
        out = encode_tigertag({})
        assert len(out) == 96
        assert out[0:4] == TIGERTAG_TAG_ID.to_bytes(4, 'big')
