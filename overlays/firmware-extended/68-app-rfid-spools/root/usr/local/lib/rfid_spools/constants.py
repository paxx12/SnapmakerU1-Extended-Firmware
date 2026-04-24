"""Filesystem paths and numeric constants used across the package."""

# ── On-disk paths ────────────────────────────────────────────────────────────
LOG_FILE = "/oem/printer_data/logs/rfid-spools.log"
CONFIG_FILE = "/oem/printer_data/config/extended/rfid-spools.json"
SYNC_STATE_FILE = "/oem/printer_data/config/extended/rfid-spools-sync-state.json"

# ── Service endpoints ────────────────────────────────────────────────────────
MOONRAKER_URL = "http://localhost"
# OpenRFID NTAG write extension endpoint (loopback HTTP server inside the
# OpenRFID daemon — see overlays/.../68-app-rfid-spools/root/usr/local/share/
# openrfid/extensions/ntag_write.py). Submitting writes through this endpoint
# avoids stopping the OpenRFID service or contending for the SPI bus.
OPENRFID_WRITE_URL = "http://127.0.0.1:8740/write"

# ── HTTP server limits ───────────────────────────────────────────────────────
MAX_CHANNELS = 4
MAX_BODY_SIZE = 64 * 1024  # 64KB max request body

# ── TigerTag encoder constants (mirror OpenRFID tag/tigertag/constants.py) ──
# See: https://github.com/suchmememanyskill/openrfid
OPENRFID_TIGERTAG_DB_DIR = "/usr/local/share/openrfid/tag/tigertag/database"
TIGERTAG_TAG_ID = 0xBC0FCB97  # newer of the two valid tag IDs
TIGERTAG_EPOCH_OFFSET = 946684800  # seconds between unix epoch and 2000-01-01
TIGERTAG_USER_DATA_LEN = 96  # bytes of user data starting at NTAG page 4
TIGERTAG_NTAG_PAGE_OFFSET = 4
TIGERTAG_NTAG_BYTE_OFFSET = TIGERTAG_NTAG_PAGE_OFFSET * 4  # 16

# ── Material density defaults (g/cm³) ────────────────────────────────────────
# Used when the user doesn't override and Spoolman requires a density.
# Key lookup is done by uppercasing the first word-token of the material string.
MATERIAL_DENSITY = {
    'PLA': 1.24, 'PLA+': 1.24,
    'ABS': 1.05, 'ASA': 1.07,
    'PETG': 1.27, 'PET': 1.27,
    'TPU': 1.21, 'TPE': 1.21, 'FLEX': 1.21,
    'PA': 1.12, 'NYLON': 1.12,
    'PC': 1.20, 'HIPS': 1.05,
    'PVA': 1.23, 'PP': 0.91,
}
DEFAULT_DENSITY = 1.24  # PLA-like safe fallback
