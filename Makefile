include vars.mk

all: tools

# ================= Build Tools =================

OUTPUT_FILE := firmware/firmware.bin

ifeq (basic,$(PROFILE))
OVERLAYS += store-version kernel-modules
OVERLAYS += enable-ssh disable-wlan-power-save
OVERLAYS += enable-native-camera-fluidd
else ifeq (extended,$(PROFILE))
OVERLAYS += store-version kernel-modules
OVERLAYS += enable-ssh disable-wlan-power-save
OVERLAYS += stub-fluidd-timelapse camera-v4l2-mpp fluidd-upgrade
OVERLAYS += rfid-support
OVERLAYS += enable-klipper-includes enable-moonraker-apprise
endif

$(OUTPUT_FILE): firmware/$(FIRMWARE_FILE) tools
ifeq (,$(OVERLAYS))
	@echo "No overlays specified. Set PROFILE variable to 'basic' or 'extended'."
	@exit 1
endif
	./scripts/create_firmware.sh $< tmp/firmware $@ $(addprefix overlays/,$(OVERLAYS))

.PHONY: build
build: $(OUTPUT_FILE)

.PHONY: extract
extract: firmware/$(FIRMWARE_FILE) tools
	./scripts/extract_squashfs.sh $< tmp/extracted

# ================= Tools =================

.PHONY: tools
tools: tools/rk2918_tools tools/upfile

tools/%: FORCE
	make -C $@

# =============== Firmware ===============

.PHONY: firmware
firmware: firmware/$(FIRMWARE_FILE)

firmware/$(FIRMWARE_FILE):
	@mkdir -p firmware
	wget -O $@.tmp "https://public.resource.snapmaker.com/firmware/U1/$(FIRMWARE_FILE)"
	echo "$(FIRMWARE_SHA256)  $@.tmp" | sha256sum -c --quiet
	mv $@.tmp $@

# ================= Test =================

test: firmware/$(FIRMWARE_FILE)
	make -C tools test FIRMWARE_FILE=$(CURDIR)/firmware/$(FIRMWARE_FILE)

# ================= Helpers =================

.PHONY: changelog
changelog:
	@echo "## Changes since last release\n"
	@git log $$(git describe --tags --abbrev=0)..HEAD --pretty=format:"- %s (%h) by @%an"

.PHONY: FORCE
FORCE:
