include vars.mk

all: tools

# ================= Build Tools =================

OUTPUT_FILE := firmware/firmware.bin

ifneq (,$(PROFILE))
PROFILE_MAIN := $(patsubst %-devel,%,$(PROFILE))
ifeq (,$(DIRTY))
OVERLAYS += $(wildcard overlays/common/*/)
endif
OVERLAYS += $(wildcard overlays/firmware-$(PROFILE_MAIN)/*/)
ifneq ($(filter %-devel,$(PROFILE)),)
OVERLAYS += $(wildcard overlays/devel/*/)
endif
endif

PROFILES := $(patsubst overlays/firmware-%,%,$(wildcard overlays/firmware-*))
PROFILES += $(patsubst overlays/firmware-%,%-devel,$(wildcard overlays/firmware-*))

$(OUTPUT_FILE): firmware/$(FIRMWARE_FILE) tools
ifeq (,$(PROFILE))
	@echo "Please specify a profile using 'make PROFILE=<profile_name>'. Available profiles are: $(PROFILES)."
	@exit 1
else ifeq (,$(filter $(PROFILE_MAIN),$(PROFILES)))
	@echo "Invalid profile '$(PROFILE_MAIN)'. Available profiles are: $(PROFILES)."
	@exit 1
endif
	./scripts/create_firmware.sh $< tmp/firmware $@ $(OVERLAYS)

.PHONY: build
build: $(OUTPUT_FILE)

.PHONY: extract
extract: firmware/$(FIRMWARE_FILE) tools
	./scripts/extract_squashfs.sh $< tmp/extracted

.PHONY: profiles
profiles:
	@echo "Available profiles: $(PROFILES)"

# ================= Tools =================

.PHONY: tools
tools: tools/rk2918_tools tools/upfile tools/resource_tool

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
