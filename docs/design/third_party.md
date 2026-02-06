---
title: Third-Party Integrations
---

# Third-Party Integrations

Third-party integrations in this firmware are handled through an on-demand download system with cryptographic verification.

## Design Principles

External components that are non-essential to core printer operations and of significant size are not bundled with the firmware image. Instead, they are:

1. Fetched on-demand when enabled by the user
2. Pinned to specific versions
3. Verified using SHA256 checksums

This reduces firmware image size, allows independent component updates, and maintains separation between core and optional functionality.

## Implementation Pattern

External components use the `*-pkg` package manager pattern. Each integration provides a shell script that handles downloading, verification, and installation.

### Example

The VPN integration (`tailscale-pkg`) demonstrates this pattern:

```bash
VERSION=1.92.5
URL="https://pkgs.tailscale.com/stable/tailscale_${VERSION}_arm64.tgz"
SHA256=13a59c3181337dfc9fdf9dea433b04c1fbf73f72ec059f64d87466b79a3a313c
```

Characteristics:
- Version pinned to `1.92.5`
- Downloads from upstream package repository
- SHA256 checksum hardcoded for verification
- Not included in firmware image
- Installed to `/oem/apps/tailscale-${VERSION}`

## Strict Versioning

Each external component is pinned to a specific version:
- Version numbers are hardcoded in the package manager script
- No automatic updates
- Upgrades require firmware update with new version and checksum
- Same firmware version fetches the same external component version

Downloads are verified using SHA256 checksums. If verification fails, installation aborts.

## Package Manager Interface

Each `*-pkg` script provides:

- `check` - verify if component is installed
- `download` - download, verify, and install component
- `clean` - remove installed component
- `update` - force re-download and reinstall (optional)

## Documentation Requirements

Third-party components must be documented in the relevant category file (e.g., `docs/vpn.md`, `docs/cloud.md`) with:

1. **Neutral technical description** - explain what the component does without promotional language
2. **Installation instructions** - how to enable and download the component
3. **Configuration** - any required setup or configuration steps
4. **Usage** - how to use the component once installed
5. **Limitations** - known constraints or issues
6. **Reference to this document** - link to this design document for technical details

Documentation must remain factual and neutral, avoiding marketing materials or subjective claims.
