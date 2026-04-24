"""In-memory and on-disk state stores."""

import json
import logging
import os
import threading
import time

from .constants import MAX_CHANNELS, SYNC_STATE_FILE


class EventBus:
    """Broadcast tag events to SSE listeners."""

    def __init__(self):
        self._lock = threading.Lock()
        self._listeners = []

    def subscribe(self):
        q = []
        with self._lock:
            self._listeners.append(q)
        return q

    def unsubscribe(self, q):
        with self._lock:
            try:
                self._listeners.remove(q)
            except ValueError:
                pass

    def publish(self, event_type, data):
        msg = 'event: {}\ndata: {}\n\n'.format(event_type, json.dumps(data))
        with self._lock:
            for q in self._listeners:
                q.append(msg)


class ChannelStore:
    """Thread-safe storage for per-channel tag data from OpenRFID webhooks."""

    def __init__(self):
        self._lock = threading.Lock()
        self._channels = {i: None for i in range(MAX_CHANNELS)}

    def update(self, channel, data):
        if not isinstance(channel, int) or channel < 0 or channel >= MAX_CHANNELS:
            return False
        with self._lock:
            self._channels[channel] = data
        return True

    def get_all(self):
        with self._lock:
            return dict(self._channels)

    def get(self, channel):
        with self._lock:
            return self._channels.get(channel)


class SyncStateStore:
    """Persists per-channel Spoolman sync state.

    Each entry is keyed by channel number (as a string) and stores
    ``filament_id``, ``spool_id``, ``uid``, and a ``synced_at`` epoch.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._state = {}
        self._load()

    def _load(self):
        try:
            with open(SYNC_STATE_FILE, 'r') as f:
                self._state = json.load(f)
        except (OSError, ValueError):
            self._state = {}

    def _save(self):
        try:
            os.makedirs(os.path.dirname(SYNC_STATE_FILE), exist_ok=True)
            with open(SYNC_STATE_FILE, 'w') as f:
                json.dump(self._state, f)
        except OSError:
            logging.exception("Failed to save sync state")

    def set(self, channel, filament_id, spool_id, uid):
        with self._lock:
            self._state[str(channel)] = {
                'filament_id': filament_id,
                'spool_id': spool_id,
                'uid': uid,
                'synced_at': int(time.time()),
            }
            self._save()

    def get(self, channel):
        with self._lock:
            return self._state.get(str(channel))

    def clear_if_uid_changed(self, channel, current_uid):
        with self._lock:
            entry = self._state.get(str(channel))
            if entry and entry.get('uid') != current_uid:
                del self._state[str(channel)]
                self._save()

    def clear(self, channel):
        with self._lock:
            if str(channel) in self._state:
                del self._state[str(channel)]
                self._save()

    def get_all(self):
        with self._lock:
            return dict(self._state)
