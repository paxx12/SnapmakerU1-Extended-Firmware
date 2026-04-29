"""Tests for ``rfid_spools.state``."""

import json

import pytest

from rfid_spools import state as state_mod
from rfid_spools.state import ChannelStore, EventBus, SyncStateStore


# ── EventBus ────────────────────────────────────────────────────────────────
class TestEventBus:
    def test_subscribe_returns_empty_queue(self):
        bus = EventBus()
        q = bus.subscribe()
        assert q == []

    def test_publish_to_single_subscriber(self):
        bus = EventBus()
        q = bus.subscribe()
        bus.publish('tag-event', {'channel': 0})
        assert len(q) == 1
        msg = q[0]
        assert msg.startswith('event: tag-event\n')
        assert 'data: {"channel": 0}' in msg
        assert msg.endswith('\n\n')

    def test_publish_fanout_to_multiple(self):
        bus = EventBus()
        a, b = bus.subscribe(), bus.subscribe()
        bus.publish('x', {'k': 1})
        assert len(a) == 1
        assert len(b) == 1

    def test_unsubscribe_removes_listener(self):
        bus = EventBus()
        a, b = bus.subscribe(), bus.subscribe()
        bus.unsubscribe(a)
        bus.publish('x', {'k': 1})
        assert a == []
        assert len(b) == 1

    def test_unsubscribe_unknown_is_noop(self):
        bus = EventBus()
        bus.unsubscribe([])  # not subscribed; must not raise


# ── ChannelStore ─────────────────────────────────────────────────────────────
class TestChannelStore:
    def test_initial_state_all_none(self):
        store = ChannelStore()
        assert store.get(0) is None
        assert store.get(1) is None

    def test_update_then_get(self):
        store = ChannelStore()
        assert store.update(0, {'tag': 'foo'}) is True
        assert store.get(0) == {'tag': 'foo'}

    def test_get_all_returns_copy(self):
        store = ChannelStore()
        store.update(0, {'tag': 'a'})
        snap = store.get_all()
        snap[0] = 'mutated'
        # Mutation of snapshot must not affect store
        assert store.get(0) == {'tag': 'a'}

    def test_update_invalid_channel_returns_false(self):
        store = ChannelStore()
        assert store.update(-1, {}) is False
        assert store.update(99, {}) is False
        assert store.update('0', {}) is False  # type-check rejects string

    def test_update_overwrites(self):
        store = ChannelStore()
        store.update(0, {'tag': 'a'})
        store.update(0, {'tag': 'b'})
        assert store.get(0) == {'tag': 'b'}


# ── SyncStateStore ───────────────────────────────────────────────────────────
@pytest.fixture
def tmp_sync_file(tmp_path, monkeypatch):
    """Redirect SyncStateStore's persistent file into a temp directory."""
    f = tmp_path / "sync-state.json"
    monkeypatch.setattr(state_mod, 'SYNC_STATE_FILE', str(f))
    return f


class TestSyncStateStore:
    def test_initial_empty(self, tmp_sync_file):
        s = SyncStateStore()
        assert s.get(0) is None
        assert s.get_all() == {}

    def test_set_and_get(self, tmp_sync_file):
        s = SyncStateStore()
        s.set(0, filament_id=10, spool_id=20, uid='AABB')
        entry = s.get(0)
        assert entry['filament_id'] == 10
        assert entry['spool_id'] == 20
        assert entry['uid'] == 'AABB'
        assert isinstance(entry['synced_at'], int)

    def test_set_persists_to_disk(self, tmp_sync_file):
        s = SyncStateStore()
        s.set(2, filament_id=1, spool_id=2, uid='X')
        assert tmp_sync_file.exists()
        loaded = json.loads(tmp_sync_file.read_text())
        assert loaded['2']['uid'] == 'X'

    def test_load_from_existing_file(self, tmp_sync_file):
        tmp_sync_file.write_text(json.dumps({'1': {'uid': 'Y', 'filament_id': 5,
                                                   'spool_id': 6, 'synced_at': 0}}))
        s = SyncStateStore()
        assert s.get(1)['uid'] == 'Y'

    def test_load_corrupt_file_falls_back_to_empty(self, tmp_sync_file):
        tmp_sync_file.write_text('{not json')
        s = SyncStateStore()
        assert s.get_all() == {}

    def test_clear_if_uid_changed_clears_when_different(self, tmp_sync_file):
        s = SyncStateStore()
        s.set(0, 1, 2, 'OLDUID')
        s.clear_if_uid_changed(0, 'NEWUID')
        assert s.get(0) is None

    def test_clear_if_uid_changed_keeps_when_same(self, tmp_sync_file):
        s = SyncStateStore()
        s.set(0, 1, 2, 'SAME')
        s.clear_if_uid_changed(0, 'SAME')
        assert s.get(0) is not None

    def test_clear_if_uid_changed_noop_when_unset(self, tmp_sync_file):
        s = SyncStateStore()
        s.clear_if_uid_changed(0, 'X')  # must not raise
        assert s.get(0) is None

    def test_clear(self, tmp_sync_file):
        s = SyncStateStore()
        s.set(0, 1, 2, 'X')
        s.clear(0)
        assert s.get(0) is None

    def test_clear_unknown_is_noop(self, tmp_sync_file):
        s = SyncStateStore()
        s.clear(0)  # not set; must not raise
