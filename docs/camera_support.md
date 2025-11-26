# Camera Support

**Available in: Extended firmware only**

The extended firmware includes hardware-accelerated camera support.

## Features

- Hardware-accelerated camera stack (Rockchip MPP/VPU)
- v4l2-mpp: MIPI CSI and USB camera support
- WebRTC low-latency streaming
- Hot-plug detection for USB cameras

## Accessing Cameras

### Internal Camera

Access the native camera at:
```
http://<printer-ip>/webcam/
```

### USB Camera

Access USB camera at:
```
http://<printer-ip>/webcam2/
```

## Enable Snapmaker's Camera Stack

Only one Camera Stack can be operational at the given moment.
Thus Snapmaker's Camera Stack is disabled by default in extended firmware.
To enable it, create:

```bash
touch /oem/.camera-native
```

## Timelapse Support

Fluidd timelapse plugin is included (no settings support).

Note: Time-lapses are not available via mobile app in cloud mode.
