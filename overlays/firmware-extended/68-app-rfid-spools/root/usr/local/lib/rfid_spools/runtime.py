"""Process-wide singletons.

The HTTP handler, the SSE publisher, and the Spoolman sync logic all need
access to the same in-memory stores. Putting them on a single small module
keeps the rest of the package free of cross-imports.
"""

from .state import ChannelStore, EventBus, SyncStateStore

event_bus = EventBus()
store = ChannelStore()
sync_state = SyncStateStore()
