TIGERTAG_VALID_DATA_IDS = {0x5BF59264, 0xBC0FCB97}

TIGERTAG_EPOCH_OFFSET = 946684800

OFF_TAG_ID = 0
OFF_PRODUCT_ID = 4
OFF_MATERIAL_ID = 8
OFF_ASPECT1_ID = 10
OFF_ASPECT2_ID = 11
OFF_TYPE_ID = 12
OFF_DIAMETER_ID = 13
OFF_BRAND_ID = 14
OFF_COLOR_RGBA = 16
OFF_WEIGHT = 20
OFF_UNIT_ID = 23
OFF_TEMP_MIN = 24
OFF_TEMP_MAX = 26
OFF_DRY_TEMP = 28
OFF_DRY_TIME = 29
OFF_BED_TEMP_MIN = 30
OFF_BED_TEMP_MAX = 31
OFF_TIMESTAMP = 32
OFF_TD = 44
OFF_METADATA = 48
# The 32-byte metadata region holds an optional emoji glyph followed by a
# UTF-8 custom message. The emoji encoding is not well-defined across writers
# (and most writers omit it), so the parser exposes the message starting at
# OFF_METADATA and lets the application strip any decorative prefix. The
# spec caps the message at 28 bytes; the trailing 4 bytes of the metadata
# region are reserved.
OFF_MESSAGE = OFF_METADATA
MESSAGE_LENGTH = 28
OFF_SIGNATURE = 80

MIN_DATA_LENGTH = 96
USER_DATA_PAGE_OFFSET = 4
USER_DATA_BYTE_OFFSET = USER_DATA_PAGE_OFFSET * 4
