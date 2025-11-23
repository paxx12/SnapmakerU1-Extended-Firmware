include vars.mk

all: tools

# ================= Build Tools =================

DEBUG_FIRMWARE_FILE := firmware/firmware_debug.bin
BASIC_FIRMWARE_FILE := firmware/firmware_basic.bin
EXTENDED_FIRMWARE_FILE := firmware/firmware_extended.bin

$(DEBUG_FIRMWARE_FILE): firmware/$(FIRMWARE_FILE) tools
	./scripts/enable_debug_misc.sh $< tmp/debug $@

$(BASIC_FIRMWARE_FILE): firmware/$(FIRMWARE_FILE) tools
	./scripts/create_firmware.sh $< tmp/basic $@ overlays/basic overlays/camera-native

$(EXTENDED_FIRMWARE_FILE): firmware/$(FIRMWARE_FILE) tools
	./scripts/create_firmware.sh $< tmp/extended $@ overlays/basic overlays/camera-new

basic_firmware: $(BASIC_FIRMWARE_FILE)
extended_firmware: $(EXTENDED_FIRMWARE_FILE)
debug_firmware: $(DEBUG_FIRMWARE_FILE)
extract_firmware: firmware/$(FIRMWARE_FILE) tools
	./scripts/extract_squashfs.sh $< tmp/extracted

# ================= Tools =================

.PHONY: tools
tools: tools/rk2918_tools tools/upfile

tools/%: FORCE
	make -C $@

# =============== Firmware ===============

firmware: firmware/$(FIRMWARE_FILE)

firmware/$(FIRMWARE_FILE):
	@mkdir -p firmware
	wget -O $@ "https://public.resource.snapmaker.com/firmware/U1/$(FIRMWARE_FILE)"
	ln -sf $@ firmware/firmware.bin

# ================= Test =================

test:
	make -C tools test FIRMWARE_FILE=$(CURDIR)/firmware/$(FIRMWARE_FILE)

# ================= Helpers =================

.PHONY: FORCE
FORCE:
