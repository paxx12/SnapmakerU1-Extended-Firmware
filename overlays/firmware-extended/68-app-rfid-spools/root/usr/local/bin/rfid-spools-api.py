#!/usr/bin/env python3
"""Entry point for the RFID Spools Management API.

The implementation lives in the ``rfid_spools`` package under
``/usr/local/lib/rfid_spools/``. This script just adds that path to
``sys.path`` and dispatches to the package's ``main()``.
"""

import sys

sys.path.insert(0, "/usr/local/lib")

from rfid_spools.server import main  # noqa: E402


if __name__ == "__main__":
    main()