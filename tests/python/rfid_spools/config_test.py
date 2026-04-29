"""Tests for ``rfid_spools.config``."""

import json

import pytest

from rfid_spools import config as config_mod
from rfid_spools.config import DEFAULT_CONFIG, load_config, save_config


@pytest.fixture
def tmp_config_file(tmp_path, monkeypatch):
    """Redirect CONFIG_FILE into a temp directory."""
    f = tmp_path / "config" / "rfid-spools.json"
    monkeypatch.setattr(config_mod, 'CONFIG_FILE', str(f))
    return f


class TestLoadConfig:
    def test_missing_file_returns_defaults(self, tmp_config_file):
        cfg = load_config()
        assert cfg['spoolman_url'] == ''
        assert cfg['slot_names'] == {}
        assert cfg['slot_notes'] == {}
        assert cfg['spoolman_extra_fields']['max_extruder_temp'] is False
        # tag_mappings must never appear in the loaded config
        assert 'tag_mappings' not in cfg

    def test_corrupt_file_returns_defaults(self, tmp_config_file):
        tmp_config_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_config_file.write_text('{not json}')
        cfg = load_config()
        assert cfg == _expected_default_shape()

    def test_legacy_tag_mappings_is_dropped(self, tmp_config_file):
        tmp_config_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_config_file.write_text(json.dumps({
            'spoolman_url': 'http://x:7912',
            'tag_mappings': {'AABB': 'ignore me'},
        }))
        cfg = load_config()
        assert cfg['spoolman_url'] == 'http://x:7912'
        assert 'tag_mappings' not in cfg

    def test_saved_value_overrides_default(self, tmp_config_file):
        tmp_config_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_config_file.write_text(json.dumps({'spoolman_url': 'http://lan:7912'}))
        cfg = load_config()
        assert cfg['spoolman_url'] == 'http://lan:7912'
        # Untouched fields keep their default
        assert cfg['slot_names'] == {}


class TestSaveConfig:
    def test_round_trip(self, tmp_config_file):
        new_cfg = dict(DEFAULT_CONFIG)
        new_cfg['spoolman_url'] = 'http://192.168.1.10:7912'
        new_cfg['slot_names'] = {'0': 'red'}
        save_config(new_cfg)
        assert tmp_config_file.exists()
        loaded = load_config()
        assert loaded['spoolman_url'] == 'http://192.168.1.10:7912'
        assert loaded['slot_names'] == {'0': 'red'}

    def test_save_creates_parent_dirs(self, tmp_config_file):
        # Parent dir doesn't exist yet
        assert not tmp_config_file.parent.exists()
        save_config({'spoolman_url': 'x'})
        assert tmp_config_file.exists()

    def test_save_is_atomic_no_tmp_left_over(self, tmp_config_file):
        save_config({'spoolman_url': 'x'})
        # The .tmp shadow file must have been renamed away
        assert not (tmp_config_file.parent / 'rfid-spools.json.tmp').exists()


def _expected_default_shape():
    """The exact dict load_config() should return for a fresh install."""
    return dict(DEFAULT_CONFIG)
