# USB Ethernet Adapters

**Available in: Basic and Extended firmware**

The custom firmware includes hot-plug support for USB ethernet adapters.

## Features

- Automatic DHCP configuration
- Hot-plug detection via udev rules
- Works with standard USB ethernet adapters

## Usage

Simply plug in a USB ethernet adapter to the printer's USB port.
The adapter will be automatically detected and configured with DHCP.

## Adapter Compatibility

Support for USB ethernet adapters may vary depending on the chipset. The following have been tested and confirmed working:

- **100M Realtek adapters**: Confirmed working
- **2.5Gbps adapters**: Confirmed working

### Reporting Compatibility Issues

If you encounter issues with your USB ethernet adapter, please share the USB IDs to help improve compatibility documentation. You can retrieve this information via SSH using:

```bash
lsusb
lsusb -t
```

Please report any non-working adapters along with their USB IDs on the GitHub issues page.
