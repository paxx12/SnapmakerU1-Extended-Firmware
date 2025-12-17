# Building from Source

## Prerequisites

### Option 1: Docker (Recommended)

- Docker installed on your system
- Use `./dev.sh` script for containerized builds

The `dev.sh` script automatically sets up a Debian Trixie ARM64 environment with all required dependencies.

### Option 2: Native Build

- Linux build environment (ARM64 or with cross-compilation support)
- `make`
- `wget`
- `squashfs-tools`
- `gcc-aarch64-linux-gnu`
- `cmake`
- `pkg-config`
- `git-core`
- `bc`
- `libssl-dev`
- `dos2unix`
- `build-essential`

## Quick Start

### Using Docker (Recommended)

Build tools and download firmware:

```bash
./dev.sh make tools
./dev.sh make firmware
```

Build basic firmware:

```bash
./dev.sh make build PROFILE=basic OUTPUT_FILE=firmware/U1_basic.bin
```

Build extended firmware:

```bash
./dev.sh make build PROFILE=extended OUTPUT_FILE=firmware/U1_extended.bin
```

Open a shell in the development environment:

```bash
./dev.sh bash
```

### Native Build

Build tools and download firmware:

```bash
make tools
make firmware
```

Build basic firmware:

```bash
sudo make build PROFILE=basic OUTPUT_FILE=firmware/U1_basic.bin
```

Build extended firmware:

```bash
sudo make build PROFILE=extended OUTPUT_FILE=firmware/U1_extended_fluidd.bin
```

**Note:** The build process requires root privileges due to squashfs root filesystem operations.

## Profiles

The build system supports two profiles:

- `basic` - simple modifications not changing key components of the firmware
- `extended` - extensive modifications changing key components of the firmware

## Overlays

Overlays are organized into categories based on their scope and build profile. Each overlay is numbered to indicate its application order within its category.

### Directory Structure

```
overlays/
├── common/                          Core overlays applied to all profiles
└── firmware-${profile}/             Profile-specific firmware overlays
```

### Overlay Structure

Each overlay directory can contain:

- `patches/` - Patch files applied to extracted firmware
- `root/` - Files copied to firmware root filesystem
- `scripts/` - Build-time scripts executed during firmware build
- `pre-scripts/` - Scripts executed before main build process

### Application Order

Overlays are applied in the following order:

1. All overlays from `common/` (in numeric order)
1. Profile-specific overlays from `firmware-${profile}/` (in numeric order)

## Project Structure

```
.
├── .github/                     Automated release builds
├── overlays/                    Profile overlay directories
│   ├── common/                  Core overlays for all profiles
│   └── firmware-${profile}/     Profile-specific firmware overlays
├── firmware/                    Downloaded and generated firmware files
├── scripts/                     Build and modification scripts
├── tmp/                         Temporary build artifacts
├── tools/                       Firmware manipulation tools
│   ├── rk2918_tools/            Rockchip image tools
│   └── upfile/                  Firmware unpacking tool
├── Makefile                     Build configuration
└── vars.mk                      Firmware version and kernel configuration
```

## Configuration

Edit `vars.mk` to configure base firmware and kernel.

## Extract Firmware

To extract and examine the base firmware:

```bash
make extract
```

Output: `tmp/extracted/`

## Release Process

The project uses GitHub Actions for automated releases:

1. Changes pushed to `main` trigger a pre-release build
2. Both basic and extended firmwares are built
3. Version is auto-incremented using `scripts/next_version.sh`
4. Release artifacts are published to GitHub Releases

## Tools

### rk2918_tools

- `afptool` - Android firmware package tool
- `img_maker` - Create Rockchip images
- `img_unpack` - Unpack Rockchip images
- `mkkrnlimg` - Create kernel images

### upfile

Firmware unpacking utility for Snapmaker update files.
