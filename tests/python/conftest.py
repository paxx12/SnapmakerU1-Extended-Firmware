"""pytest configuration: make overlay packages importable.

Each overlay's Python code lives at the same path it has on the printer
(``root/usr/local/lib/<package>/``). We add those package roots to
``sys.path`` so tests can ``import rfid_spools.spoolman`` etc. directly.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

_OVERLAY_LIB_PATHS = [
    _REPO_ROOT / "overlays" / "firmware-extended" / "68-app-rfid-spools"
                / "root" / "usr" / "local" / "lib",
]

for p in _OVERLAY_LIB_PATHS:
    s = str(p)
    if p.exists() and s not in sys.path:
        sys.path.insert(0, s)
