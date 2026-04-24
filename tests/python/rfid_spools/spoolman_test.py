"""Tests for ``rfid_spools.spoolman`` — pure-function helpers + mocked HTTP."""

import json
from unittest.mock import patch

import pytest

from rfid_spools import spoolman
from rfid_spools.spoolman import (
    _build_extra_payload,
    _float_pos,
    _int_pos,
    _resolve_density,
    _upsert_vendor,
    resolve_display_fields,
)


# ── resolve_display_fields ───────────────────────────────────────────────────
class TestResolveDisplayFields:
    def test_uid_from_scan_list(self):
        ev = {'scan': {'uid': [0xA1, 0xB2, 0xC3, 0xD4]},
              'filament': {'manufacturer': 'X'}}
        assert resolve_display_fields(ev)['uid'] == 'A1B2C3D4'

    def test_uid_from_scan_string(self):
        ev = {'scan': {'uid': 'DEADBEEF'}, 'filament': {}}
        assert resolve_display_fields(ev)['uid'] == 'DEADBEEF'

    def test_uid_falls_back_to_card_uid_list(self):
        ev = {'scan': {}, 'filament': {'CARD_UID': [0x01, 0x02, 0x0A]}}
        assert resolve_display_fields(ev)['uid'] == '01020A'

    def test_uid_falls_back_to_card_uid_lowercase_key(self):
        ev = {'scan': {}, 'filament': {'card_uid': 'beefcafe'}}
        assert resolve_display_fields(ev)['uid'] == 'beefcafe'

    def test_uid_none_when_unset(self):
        ev = {'scan': {}, 'filament': {}}
        assert resolve_display_fields(ev)['uid'] is None

    def test_bed_temp_cascade_min_only(self):
        ev = {'filament': {'bed_temp_c': 60}}
        out = resolve_display_fields(ev)
        assert out['bed_temp_min_c'] == 60
        assert out['bed_temp_max_c'] == 60

    def test_bed_temp_cascade_max_only(self):
        ev = {'filament': {'bed_temp_max_c': 80}}
        out = resolve_display_fields(ev)
        assert out['bed_temp_min_c'] == 80
        assert out['bed_temp_max_c'] == 80

    def test_bed_temp_both_kept(self):
        ev = {'filament': {'bed_temp_c': 55, 'bed_temp_max_c': 75}}
        out = resolve_display_fields(ev)
        assert out['bed_temp_min_c'] == 55
        assert out['bed_temp_max_c'] == 75

    def test_empty_strings_become_none(self):
        ev = {'filament': {'manufacturer': '', 'type': 'PLA'}}
        out = resolve_display_fields(ev)
        assert out['manufacturer'] is None
        assert out['type'] == 'PLA'

    def test_passes_through_known_fields(self):
        ev = {'filament': {
            'manufacturer': 'Bambu', 'type': 'PLA Basic',
            'modifiers': 'Matte', 'colors': [0xFFFF0000],
            'hotend_min_temp_c': 200, 'hotend_max_temp_c': 230,
            'diameter_mm': 1.75, 'weight_grams': 1000,
            'drying_temp_c': 45, 'drying_time_hours': 8,
            'manufacturing_date': '20240101', 'td': 1.5,
            'message': 'hi',
        }}
        out = resolve_display_fields(ev)
        for k in ev['filament']:
            assert out[k if k != 'bed_temp_c' else 'bed_temp_min_c'] == ev['filament'][k]


# ── _resolve_density ─────────────────────────────────────────────────────────
class TestResolveDensity:
    def test_explicit_value_wins(self):
        assert _resolve_density(2.5, 'PLA') == 2.5

    def test_explicit_zero_falls_back_to_material(self):
        assert _resolve_density(0, 'PLA') == 1.24

    def test_explicit_negative_falls_back(self):
        assert _resolve_density(-1, 'ABS') == 1.05

    def test_string_density(self):
        assert _resolve_density('1.5', 'PLA') == 1.5

    def test_garbage_density_falls_back(self):
        assert _resolve_density('garbage', 'PETG') == 1.27

    def test_material_lookup_uppercases(self):
        assert _resolve_density(None, 'pla') == 1.24

    def test_material_lookup_first_token(self):
        # Splits on whitespace and dash, takes first
        assert _resolve_density(None, 'PLA Basic') == 1.24
        assert _resolve_density(None, 'PLA-CF') == 1.24

    def test_unknown_material_uses_default(self):
        assert _resolve_density(None, 'XYZ') == 1.24

    def test_no_material_uses_default(self):
        assert _resolve_density(None, None) == 1.24


# ── _int_pos / _float_pos ────────────────────────────────────────────────────
class TestNumericGuards:
    def test_int_pos_happy(self):
        assert _int_pos(42) == 42
        assert _int_pos('42') == 42
        assert _int_pos('42.7') == 42  # truncates

    def test_int_pos_zero_returns_none(self):
        assert _int_pos(0) is None

    def test_int_pos_negative_returns_none(self):
        assert _int_pos(-5) is None

    def test_int_pos_garbage(self):
        assert _int_pos('foo') is None
        assert _int_pos(None) is None

    def test_float_pos_happy(self):
        assert _float_pos(1.75) == 1.75
        assert _float_pos('1.75') == 1.75

    def test_float_pos_zero_returns_none(self):
        assert _float_pos(0) is None
        assert _float_pos(0.0) is None

    def test_float_pos_garbage(self):
        assert _float_pos('foo') is None


# ── _build_extra_payload ─────────────────────────────────────────────────────
class TestBuildExtraPayload:
    def test_empty_returns_none(self):
        assert _build_extra_payload({}, None) is None
        assert _build_extra_payload({}, {}) is None

    def test_int_field_serializes_as_int_string(self):
        out = _build_extra_payload(
            {'hotend_max_temp_c': 250},
            {'max_extruder_temp': True}
        )
        assert out == {'max_extruder_temp': '250'}

    def test_int_field_strips_decimal(self):
        # bed_temp_max_c arriving as a float-string "60.0" must become "60"
        out = _build_extra_payload(
            {'bed_temp_max_c': '60.0'},
            {'max_bed_temp': True}
        )
        assert out == {'max_bed_temp': '60'}

    def test_text_field_is_json_quoted(self):
        out = _build_extra_payload(
            {'modifiers': 'Matte'},
            {'modifiers': True}
        )
        assert out == {'modifiers': '"Matte"'}
        # Round-trips through json
        assert json.loads(out['modifiers']) == 'Matte'

    def test_datetime_field_is_normalized_then_json_quoted(self):
        out = _build_extra_payload(
            {'manufacturing_date': '20240315'},
            {'mfg_date': True}
        )
        assert out == {'mfg_date': '"2024-03-15T00:00:00"'}

    def test_float_field_left_as_string(self):
        # td is float type — Spoolman accepts the bare decimal as JSON number
        out = _build_extra_payload(
            {'td': 1.5},
            {'td': True}
        )
        assert out == {'td': '1.5'}

    def test_disabled_field_ignored(self):
        out = _build_extra_payload(
            {'hotend_max_temp_c': 250, 'modifiers': 'Matte'},
            {'max_extruder_temp': False, 'modifiers': True}
        )
        assert out == {'modifiers': '"Matte"'}

    def test_missing_value_skipped(self):
        out = _build_extra_payload(
            {'modifiers': 'Matte'},
            {'modifiers': True, 'max_extruder_temp': True}
        )
        assert out == {'modifiers': '"Matte"'}

    def test_list_value_joined(self):
        out = _build_extra_payload(
            {'modifiers': ['Matte', 'CF']},
            {'modifiers': True}
        )
        assert out == {'modifiers': '"Matte, CF"'}


# ── _upsert_vendor ───────────────────────────────────────────────────────────
class TestUpsertVendor:
    def test_no_manufacturer_returns_none(self):
        assert _upsert_vendor('http://x', None) is None
        assert _upsert_vendor('http://x', '') is None

    def test_existing_vendor_returns_id(self):
        with patch.object(spoolman, 'spoolman_api_request',
                          return_value=[{'id': 7, 'name': 'Bambu'}]) as m:
            assert _upsert_vendor('http://x', 'Bambu') == 7
        m.assert_called_once()
        # First (and only) call must be the GET lookup
        method, path = m.call_args[0][1], m.call_args[0][2]
        assert method == 'GET'
        assert '/api/v1/vendor?name=' in path
        assert 'Bambu' in path

    def test_creates_when_missing(self):
        calls = []

        def fake(_base, method, path, body=None):
            calls.append((method, path, body))
            if method == 'GET':
                return []  # not found
            if method == 'POST':
                return {'id': 42}
            pytest.fail("unexpected call")

        with patch.object(spoolman, 'spoolman_api_request', side_effect=fake):
            assert _upsert_vendor('http://x', 'NewBrand') == 42
        assert calls[0][0] == 'GET'
        assert calls[1] == ('POST', '/api/v1/vendor', {'name': 'NewBrand'})

    def test_url_encodes_manufacturer(self):
        captured = {}

        def fake(_base, method, path, body=None):
            captured['path'] = path
            return [{'id': 1}]

        with patch.object(spoolman, 'spoolman_api_request', side_effect=fake):
            _upsert_vendor('http://x', 'Co & Friends')
        assert 'Co%20%26%20Friends' in captured['path']
