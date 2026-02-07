# CLAUDE.md - AI Assistant Guide

This document provides guidance for AI assistants working with the Snapmaker U1 Extended Firmware codebase.

## Project Overview

This project builds custom firmware for the **Snapmaker U1 3D printer**, enabling debug features like SSH access and adding capabilities like hardware-accelerated camera streaming, RFID support, remote screen access, and monitoring integrations.

**Key characteristics:**
- ARM64 embedded Linux firmware for Rockchip-based 3D printer
- Overlay-based firmware modification system
- Docker-based cross-compilation environment
- GitHub Actions CI/CD for automated builds and releases

## Repository Structure

```
.
├── .github/
│   ├── dev/Dockerfile          # Development container (Debian Trixie ARM64)
│   └── workflows/
│       ├── pre_release.yaml    # Release builds on main/stable-* branches
│       └── pull_request.yaml   # PR and develop branch builds
├── overlays/                   # Firmware modifications (see Overlay System below)
│   ├── common/                 # Applied to ALL profiles
│   ├── devel/                  # Development tools (only with -devel suffix)
│   ├── firmware-basic/         # Basic profile overlays
│   ├── firmware-extended/      # Extended profile overlays
│   └── staging/                # Disabled/experimental overlays
├── scripts/
│   ├── create_firmware.sh      # Main firmware build script
│   ├── extract_squashfs.sh     # Extract firmware for inspection
│   ├── next_version.sh         # Version auto-increment for releases
│   └── helpers/                # pack/unpack/chroot helpers
├── tools/
│   ├── rk2918_tools/           # Rockchip image manipulation (afptool, img_maker, etc.)
│   ├── upfile/                 # Snapmaker firmware unpacker
│   └── resource_tool/          # Boot logo resource tool
├── docs/                       # User documentation (Jekyll-based)
├── deps/                       # Git submodules
├── Makefile                    # Build orchestration
├── vars.mk                     # Firmware version and kernel configuration
└── dev.sh                      # Docker development environment wrapper
```

## Build System

### Development Environment

All builds run inside a Docker container to ensure consistent ARM64 cross-compilation:

```bash
./dev.sh make <target>    # Run make target in container
./dev.sh bash             # Open shell in container
```

### Common Build Commands

```bash
# Build tools (required first)
./dev.sh make tools

# Download base firmware
./dev.sh make firmware

# Build firmware profiles
./dev.sh make build PROFILE=basic OUTPUT_FILE=firmware/U1_basic.bin
./dev.sh make build PROFILE=extended OUTPUT_FILE=firmware/U1_extended.bin

# Development builds (include devel overlays)
./dev.sh make build PROFILE=basic-devel
./dev.sh make build PROFILE=extended-devel

# Extract firmware for inspection
./dev.sh make extract
# Output in: tmp/extracted/

# List available profiles
make profiles
```

### Build Profiles

| Profile | Description |
|---------|-------------|
| `basic` | Stock firmware + SSH + minimal modifications |
| `extended` | Full features: camera stack, RFID, remote screen, monitoring |
| `*-devel` | Any profile + development tools (Entware package manager) |

## Overlay System

Overlays are modular firmware modifications applied in numbered order.

### Overlay Structure

Each overlay directory can contain:
```
overlays/<category>/NN-overlay-name/
├── patches/          # .patch files applied to extracted rootfs
├── root/             # Files copied directly to rootfs (preserves permissions)
├── scripts/          # Build-time scripts (run AFTER patches, receive $1=rootfs path)
└── pre-scripts/      # Scripts run BEFORE patches (receive $1=rootfs path)
```

### Application Order

1. `common/*` overlays (all profiles)
2. `firmware-{profile}/*` overlays (profile-specific)
3. `devel/*` overlays (only if `-devel` suffix used)

Within each category, overlays apply in numeric order (01-, 02-, etc.).

### Overlay Script Patterns

Build scripts receive the rootfs directory as the first argument:

```bash
#!/bin/bash
if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <rootfs-dir>"
  exit 1
fi

set -eo pipefail
ROOTFS_DIR="$(realpath "$1")"

# Cross-compilation environment (if needed)
export CROSS_COMPILE=aarch64-linux-gnu-
export CC="${CROSS_COMPILE}gcc"

# Do work...
```

### Patch Format

Patches use unified diff format with `-p1` strip level, relative to rootfs:
```patch
--- a/etc/some/config
+++ b/etc/some/config
@@ -1,3 +1,3 @@
 line1
-old line
+new line
 line3
```

## Key Configuration Files

### vars.mk
Contains base firmware version and kernel configuration:
```makefile
FIRMWARE_FILE=U1_1.0.0.158_20251230140122_upgrade.bin
FIRMWARE_VERSION=1.0.0
FIRMWARE_SHA256=e1079ed43d41fff7411770d7bbc3857068bd4b1d3570babf07754e2dd9cbfc2e
KERNEL_GIT_URL=https://github.com/rockchip-linux/kernel.git
KERNEL_SHA=8533b2249e1550b233a4836d039d64e3bb2fed7a
```

### User Configuration (on device)
Extended firmware users configure via INI-style file at:
```
/home/lava/printer_data/config/extended/extended.cfg
```

## CI/CD Workflows

### Pull Request / Develop Branch
- Builds all profiles (basic, extended, basic-devel, extended-devel)
- Uploads artifacts for testing
- Comments on PR with download links

### Release (main branch)
- Builds basic and extended profiles
- Auto-increments version via `scripts/next_version.sh`
- Creates GitHub pre-release with firmware binaries

## Code Conventions

### File Ownership

The firmware uses specific UID/GID for files:
- **Root files**: UID 0, GID 0
- **User files** (under `/home/lava/`): UID 1000, GID 1000

The build system validates ownership preservation.

### Binary Validation

All binaries in the rootfs must be ARM architecture. The build fails if non-ARM ELF binaries are detected.

### Script Naming

- Scripts numbered NN- for ordering: `01-first.sh`, `02-second.sh`
- Patches similarly numbered within their directory
- Use descriptive names indicating purpose

### External Dependencies

For external code dependencies:
1. Pin to specific git SHA for reproducibility
2. Clone to `tmp/` during build (excluded from git)
3. Validate installed binaries exist after build

Example from `01-v4l2-mpp.sh`:
```bash
GIT_URL=https://github.com/paxx12/v4l2-mpp.git
GIT_SHA=468fe35b159977a6e86f75f5e9024cb404eaa71d
```

## Common Tasks for AI Assistants

### Adding a New Overlay

1. Create numbered directory in appropriate category:
   ```
   overlays/firmware-extended/NN-feature-name/
   ```

2. Add relevant subdirectories (`patches/`, `root/`, `scripts/`)

3. Ensure scripts are executable and follow the pattern above

4. Test build: `./dev.sh make build PROFILE=extended`

### Modifying Existing Firmware Files

1. Extract firmware: `./dev.sh make extract`
2. Find file in `tmp/extracted/`
3. Create patch file in overlay's `patches/` directory
4. Use `-p1` strip level from rootfs root

### Updating Base Firmware Version

1. Edit `vars.mk`:
   - Update `FIRMWARE_FILE` with new filename
   - Update `FIRMWARE_VERSION`
   - Update `FIRMWARE_SHA256` (sha256sum of file)

2. Test: `./dev.sh make firmware && ./dev.sh make build PROFILE=extended`

### Adding Documentation

Documentation lives in `docs/` using Jekyll with GitHub Pages:
- Use YAML front matter with `title:`
- Markdown with standard formatting
- Link to other docs with relative paths

## Important Paths on Target Device

| Path | Description |
|------|-------------|
| `/home/lava/` | Main user home (UID 1000) |
| `/home/lava/printer_data/config/` | Klipper/Moonraker configuration |
| `/home/lava/printer_data/config/extended/` | Extended firmware configuration |
| `/userdata/extended/` | Persistent user data across reboots |
| `/oem/printer_data/` | OEM data partition |
| `/var/log/messages` | System log |

## Testing

### Local Testing

```bash
# Run tool tests
make -C tools test FIRMWARE_FILE=$(pwd)/firmware/U1_*.bin
```

### On-Device Testing

1. Build firmware with changes
2. Copy `.bin` to FAT32 USB drive
3. On printer: Settings > About > Firmware Version > Local Update
4. SSH in (`ssh root@<ip>`, password: `snapmaker`) to verify changes

## Submodules and Dependencies

The project uses git submodules in `deps/`:
```bash
git submodule update --init --recursive
```

Key external dependencies:
- **v4l2-mpp**: Hardware-accelerated camera stack (cloned during build)
- **screen-apps**: Remote screen components (submodule)

## Warnings

- **Never commit** firmware binaries, `tmp/`, or build artifacts
- **Preserve file permissions** - the squashfs requires correct ownership
- **Cross-compile only** - all binaries must be ARM64
- **Test thoroughly** - bad firmware can make the printer unbootable (revert with stock firmware)

## Related Resources

- [User Documentation](https://snapmakeru1-extended-firmware.pages.dev/)
- [v4l2-mpp Repository](https://github.com/paxx12/v4l2-mpp)
- [Snapmaker Discord #u1-printer](https://discord.com/invite/snapmaker-official-1086575708903571536)
