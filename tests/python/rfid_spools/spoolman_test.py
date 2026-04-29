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


# ── fetch_inventory_counts ───────────────────────────────────────────────────
class TestFetchInventoryCounts:
    def test_happy_path_uses_x_total_count(self):
        def fake(_base, _method, path, body=None):
            # path includes ?limit=1 appended by _safe_count
            assert 'limit=1' in path
            if path.startswith('/api/v1/spool'):
                return [{}], {'x-total-count': '42'}
            if path.startswith('/api/v1/filament'):
                return [{}], {'x-total-count': '17'}
            if path.startswith('/api/v1/vendor'):
                return [{}], {'x-total-count': '5'}
            pytest.fail("unexpected path: " + path)

        with patch.object(spoolman, 'spoolman_api_request_with_headers',
                          side_effect=fake):
            assert spoolman.fetch_inventory_counts('http://x') == {
                'spools': 42, 'filaments': 17, 'vendors': 5,
            }

    def test_falls_back_to_len_when_header_missing(self):
        def fake(_base, _method, _path, body=None):
            return [{}, {}, {}], {}  # no x-total-count

        with patch.object(spoolman, 'spoolman_api_request_with_headers',
                          side_effect=fake):
            out = spoolman.fetch_inventory_counts('http://x')
        assert out == {'spools': 3, 'filaments': 3, 'vendors': 3}

    def test_individual_failure_returns_none_for_that_count(self):
        def fake(_base, _method, path, body=None):
            if path.startswith('/api/v1/filament'):
                raise RuntimeError('boom')
            return [{}], {'x-total-count': '9'}

        with patch.object(spoolman, 'spoolman_api_request_with_headers',
                          side_effect=fake):
            out = spoolman.fetch_inventory_counts('http://x')
        assert out == {'spools': 9, 'filaments': None, 'vendors': 9}

    def test_garbage_header_falls_back_to_len(self):
        def fake(_base, _method, _path, body=None):
            return [{}, {}], {'x-total-count': 'not-a-number'}

        with patch.object(spoolman, 'spoolman_api_request_with_headers',
                          side_effect=fake):
            out = spoolman.fetch_inventory_counts('http://x')
        assert out == {'spools': 2, 'filaments': 2, 'vendors': 2}

    def test_non_list_payload_returns_none(self):
        def fake(_base, _method, _path, body=None):
            return {'unexpected': 'shape'}, {}

        with patch.object(spoolman, 'spoolman_api_request_with_headers',
                          side_effect=fake):
            out = spoolman.fetch_inventory_counts('http://x')
        assert out == {'spools': None, 'filaments': None, 'vendors': None}


# ── list_all_spools / get_spool / cache ─────────────────────────────────────
@pytest.fixture(autouse=True)
def _clear_spool_cache():
    """The bulk-spool cache is module-global; reset it around every test in
    this file so cached results from one test never leak into another."""
    spoolman.invalidate_spool_cache()
    yield
    spoolman.invalidate_spool_cache()


def _mk_spool(sid, vendor='Bambu', material='PLA', name='Basic',
              color='#ff0000', weight=1000, archived=False):
    return {
        'id': sid,
        'remaining_weight': 800,
        'last_used': '2025-01-01T00:00:00Z',
        'archived': archived,
        'filament': {
            'id': sid * 10,
            'external_id': 'EXT{}'.format(sid),
            'name': name,
            'material': material,
            'color_hex': color,
            'weight': weight,
            'vendor': {'id': 1, 'name': vendor},
        },
    }


class TestListAllSpools:
    def test_single_page(self):
        page = [_mk_spool(i) for i in range(1, 4)]
        with patch.object(spoolman, 'spoolman_api_request',
                          return_value=page):
            out = spoolman.list_all_spools('http://x')
        assert out['count'] == 3
        assert out['truncated'] is False
        assert out['items'][0]['vendor'] == 'Bambu'
        assert out['items'][0]['external_id'] == 'EXT1'

    def test_multi_page_concatenation(self):
        # PAGE_SIZE=500: first call returns a full page → keep paging.
        page1 = [_mk_spool(i) for i in range(1, 501)]
        page2 = [_mk_spool(i) for i in range(501, 503)]
        calls = []

        def fake(_base, _method, path, body=None):
            calls.append(path)
            return page1 if 'offset=0' in path else page2

        with patch.object(spoolman, 'spoolman_api_request', side_effect=fake):
            out = spoolman.list_all_spools('http://x')
        assert out['count'] == 502
        assert out['truncated'] is False
        assert len(calls) == 2
        assert 'offset=500' in calls[1]

    def test_empty_result(self):
        with patch.object(spoolman, 'spoolman_api_request', return_value=[]):
            out = spoolman.list_all_spools('http://x')
        assert out == {
            'items': [], 'count': 0, 'truncated': False,
            'fetched_at': out['fetched_at'],
        }

    def test_truncation_at_hard_cap(self, monkeypatch):
        # Lower the cap so we can hit it with a small fixture.
        monkeypatch.setattr(spoolman, 'SPOOL_BULK_HARD_CAP', 3)
        monkeypatch.setattr(spoolman, 'SPOOL_BULK_PAGE_SIZE', 2)
        page1 = [_mk_spool(1), _mk_spool(2)]   # full page → keep going
        page2 = [_mk_spool(3), _mk_spool(4)]   # cap of 3 stops mid-page

        def fake(_base, _method, path, body=None):
            return page1 if 'offset=0' in path else page2

        with patch.object(spoolman, 'spoolman_api_request', side_effect=fake):
            out = spoolman.list_all_spools('http://x')
        assert out['count'] == 3
        assert out['truncated'] is True

    def test_archived_toggle_changes_query(self):
        captured = []

        def fake(_base, _method, path, body=None):
            captured.append(path)
            return []

        with patch.object(spoolman, 'spoolman_api_request', side_effect=fake):
            spoolman.list_all_spools('http://x', include_archived=False)
            spoolman.invalidate_spool_cache()
            spoolman.list_all_spools('http://x', include_archived=True)
        assert 'allow_archived' not in captured[0]
        assert 'allow_archived=true' in captured[1]

    def test_cache_hit_within_ttl(self):
        with patch.object(spoolman, 'spoolman_api_request',
                          return_value=[_mk_spool(1)]) as m:
            spoolman.list_all_spools('http://x')
            spoolman.list_all_spools('http://x')
        assert m.call_count == 1  # second call served from cache

    def test_cache_miss_after_invalidate(self):
        with patch.object(spoolman, 'spoolman_api_request',
                          return_value=[_mk_spool(1)]) as m:
            spoolman.list_all_spools('http://x')
            spoolman.invalidate_spool_cache()
            spoolman.list_all_spools('http://x')
        assert m.call_count == 2

    def test_force_refresh_bypasses_cache(self):
        with patch.object(spoolman, 'spoolman_api_request',
                          return_value=[_mk_spool(1)]) as m:
            spoolman.list_all_spools('http://x')
            spoolman.list_all_spools('http://x', force_refresh=True)
        assert m.call_count == 2

    def test_cache_keyed_by_archived_flag(self):
        """Toggling include_archived must not reuse the previous payload."""
        with patch.object(spoolman, 'spoolman_api_request',
                          return_value=[_mk_spool(1)]) as m:
            spoolman.list_all_spools('http://x', include_archived=False)
            spoolman.list_all_spools('http://x', include_archived=True)
        assert m.call_count == 2


class TestGetSpool:
    def test_happy_path(self):
        with patch.object(spoolman, 'spoolman_api_request',
                          return_value=_mk_spool(7, vendor='Polymaker')):
            out = spoolman.get_spool('http://x', 7)
        assert out['id'] == 7
        assert out['vendor'] == 'Polymaker'

    def test_404_returns_none(self):
        import urllib.error

        def raise_404(_b, _m, _p, body=None):
            raise urllib.error.HTTPError('http://x/api/v1/spool/9',
                                         404, 'Not Found', {}, None)

        with patch.object(spoolman, 'spoolman_api_request',
                          side_effect=raise_404):
            assert spoolman.get_spool('http://x', 9) is None

    def test_non_numeric_id_returns_none(self):
        # Should never hit Spoolman.
        with patch.object(spoolman, 'spoolman_api_request') as m:
            assert spoolman.get_spool('http://x', 'abc') is None
            assert spoolman.get_spool('http://x', None) is None
            assert spoolman.get_spool('http://x', 0) is None
            assert spoolman.get_spool('http://x', -1) is None
        m.assert_not_called()

    def test_other_http_error_propagates(self):
        import urllib.error

        def raise_500(_b, _m, _p, body=None):
            raise urllib.error.HTTPError('http://x/api/v1/spool/1',
                                         500, 'Server Error', {}, None)

        with patch.object(spoolman, 'spoolman_api_request',
                          side_effect=raise_500):
            with pytest.raises(urllib.error.HTTPError):
                spoolman.get_spool('http://x', 1)


# ── spool_to_tigertag_spec ──────────────────────────────────────────────────
class TestSpoolToTigertagSpec:
    def _full(self, **overrides):
        spool = {
            'id': 42,
            'initial_weight': 1000,
            'filament': {
                'id': 7,
                'name': 'Bambu PLA Basic Black',
                'material': 'PLA',
                'color_hex': 'FF0000',
                'diameter': 1.75,
                'weight': 1000,
                'settings_extruder_temp': 215,
                'settings_bed_temp': 60,
                'extra': {
                    'drying_temp': '50',
                    'drying_time': '8',
                    'td': '1.6',
                    'mfg_date': '"2024-06-01"',
                    'modifiers': '"Matte, Silk"',
                },
                'vendor': {'id': 1, 'name': 'Bambu Lab'},
            },
        }
        spool.update(overrides)
        return spool

    def test_full_data_maps_correctly(self):
        out = spoolman.spool_to_tigertag_spec(self._full())
        assert out['manufacturer'] == 'Bambu Lab'
        assert out['type'] == 'PLA'
        assert out['rgb1'] == 0xFF0000
        assert out['hotend_min_temp_c'] == 215
        assert out['hotend_max_temp_c'] == 215
        assert out['bed_temp_min_c'] == 60
        assert out['bed_temp_max_c'] == 60
        assert out['diameter_mm'] == 1.75
        assert out['weight_grams'] == 1000
        assert out['drying_temp_c'] == 50
        assert out['drying_time_hours'] == 8
        assert out['td'] == 1.6
        assert out['manufacturing_date'] == '2024-06-01'
        assert out['modifiers'] == ['Matte', 'Silk']
        assert out['unit'] == 'g'
        assert out['source'] == 'spoolman'
        assert out['source_spool_id'] == 42
        assert out['source_filament_id'] == 7

    def test_message_default_truncated_to_28_bytes(self):
        spool = self._full()
        # Drop the filament name so we exercise the {vendor} {material}
        # fallback path that has the only string long enough to truncate.
        spool['filament']['name'] = ''
        spool['filament']['vendor']['name'] = 'A Very Long Vendor Name Indeed'
        spool['filament']['material'] = 'PLA-CF'
        out = spoolman.spool_to_tigertag_spec(spool)
        assert len(out['message'].encode('utf-8')) <= 28
        assert out['message'].startswith('A Very Long Vendor Name')

    def test_message_uses_filament_name(self):
        spool = self._full()
        out = spoolman.spool_to_tigertag_spec(spool)
        # Filament name is the most informative label for the user; it wins
        # over the {vendor} {material} fallback when present.
        assert out['message'] == 'Bambu PLA Basic Black'

    def test_missing_vendor_name(self):
        spool = self._full()
        spool['filament']['name'] = ''  # force fallback to {vendor} {material}
        spool['filament']['vendor'] = {}
        out = spoolman.spool_to_tigertag_spec(spool)
        assert out['manufacturer'] is None
        # Message becomes just the material
        assert out['message'] == 'PLA'

    def test_missing_temps_returns_none(self):
        spool = self._full()
        del spool['filament']['settings_extruder_temp']
        del spool['filament']['settings_bed_temp']
        out = spoolman.spool_to_tigertag_spec(spool)
        assert out['hotend_min_temp_c'] is None
        assert out['bed_temp_max_c'] is None

    def test_color_priority_spool_wins(self):
        spool = self._full()
        spool['extra'] = {'color_hex': '"00FF00"'}  # Spoolman extras are JSON-encoded
        out = spoolman.spool_to_tigertag_spec(spool)
        assert out['rgb1'] == 0x00FF00

    def test_color_with_hash_prefix(self):
        spool = self._full()
        spool['filament']['color_hex'] = '#ABCDEF'
        out = spoolman.spool_to_tigertag_spec(spool)
        assert out['rgb1'] == 0xABCDEF

    def test_invalid_color_returns_none_rgb(self):
        spool = self._full()
        spool['filament']['color_hex'] = 'not-a-color'
        out = spoolman.spool_to_tigertag_spec(spool)
        assert out['rgb1'] is None

    def test_modifiers_as_list(self):
        spool = self._full()
        spool['filament']['extra']['modifiers'] = '["Glow", "CF"]'
        out = spoolman.spool_to_tigertag_spec(spool)
        assert out['modifiers'] == ['Glow', 'CF']

    def test_modifiers_missing(self):
        spool = self._full()
        del spool['filament']['extra']['modifiers']
        out = spoolman.spool_to_tigertag_spec(spool)
        assert out['modifiers'] == []

    def test_explicit_filament_and_vendor_overrides(self):
        # Caller can pass split records — used by fetch_spool_with_relations
        # when the embedded record is thin.
        spool = {'id': 5, 'initial_weight': 750}
        filament = {'id': 9, 'material': 'PETG', 'diameter': 1.75}
        vendor = {'id': 2, 'name': 'Polymaker'}
        out = spoolman.spool_to_tigertag_spec(spool, filament, vendor)
        assert out['type'] == 'PETG'
        assert out['manufacturer'] == 'Polymaker'
        assert out['weight_grams'] == 750  # falls back to spool initial_weight
        assert out['source_spool_id'] == 5

    def test_empty_spool_does_not_crash(self):
        out = spoolman.spool_to_tigertag_spec({})
        assert out['manufacturer'] is None
        assert out['type'] is None
        assert out['message'] is None
