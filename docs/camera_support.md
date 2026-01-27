---
title: Camera Support
---

# Camera Support

**Available in: Extended firmware only**

The extended firmware includes hardware-accelerated camera support with WebRTC streaming.

## Features

- Hardware-accelerated camera stack (Rockchip MPP/VPU) with WebRTC streaming
- MIPI CSI internal camera and USB camera support
- Low-latency WebRTC streaming (best quality and performance)
- Hot-plug detection for USB cameras
- Web-based camera controls with settings persistence
- Optional RTSP streaming support
- Compatible with AI detection and Snapmaker Cloud features

## Accessing Cameras

### Internal Camera

Access at: `http://<printer-ip>/webcam/`

The internal camera is automatically configured and enabled.

### USB Camera

Access at: `http://<printer-ip>/webcam2/`

USB cameras must be enabled in `extended.cfg`. See [USB Camera Configuration](#usb-camera-configuration) below for setup instructions.

## Moonraker Camera Configuration

Camera streaming settings are configured through Moonraker configuration files in the `extended/moonraker/` directory.

### Internal Camera Configuration

Edit `extended/moonraker/02_internal_camera.cfg` to customize internal camera streaming:

```cfg
[webcam case]
service: webrtc-camerastreamer
stream_url: /webcam/webrtc
snapshot_url: /webcam/snapshot.jpg
aspect_ratio: 16:9
```

**Available streaming modes:**
- `webrtc-camerastreamer` - WebRTC streaming (best quality and performance, default)
  - `stream_url: /webcam/webrtc`
- `iframe` - H264/MJPEG iframe streaming (acceptable quality and performance)
  - `stream_url: /webcam/player`
- `mjpegstreamer-adaptive` - MJPEG streaming (best compatibility, most resource intensive)
  - No stream_url needed (uses snapshot_url only)

### USB Camera Configuration

Edit `extended/moonraker/03_usb_camera.cfg` to enable USB camera. Uncomment one of the sections:

```cfg
[webcam usb]
service: webrtc-camerastreamer
stream_url: /webcam2/webrtc
snapshot_url: /webcam2/snapshot.jpg
aspect_ratio: 16:9
```

**Important:** Only one streaming mode can be active per camera. After changing camera configuration, reboot the printer.

## Camera Controls

**Note: Camera controls and RTSP streaming are only available with the paxx12 camera stack.**

The paxx12 camera stack includes a web-based interface for adjusting camera settings in real-time. Available controls depend on your camera hardware capabilities.

### Accessing Camera Controls

Camera controls are accessible at:
- Internal camera: `http://<printer-ip>/webcam/control`
- USB camera: `http://<printer-ip>/webcam2/control`

### Settings Persistence

Camera settings are automatically saved across reboots:
- Internal camera: `/oem/printer_data/config/extended/camera/case.json`
- USB camera: `/oem/printer_data/config/extended/camera/usb.json`

To reset camera settings to defaults, delete the corresponding JSON file and reboot the printer.

## Configuration

All camera configuration is done through `/home/lava/printer_data/config/extended/extended.cfg`. See [Firmware Configuration](firmware_config.md) for editing instructions.

### Camera Stack Selection

By default, the extended firmware uses a custom hardware-accelerated camera stack (paxx12). To switch to Snapmaker's original camera stack:

```ini
[camera]
stack: snapmaker
```

Note: Only one camera stack can be operational at a time.

### Camera Logging

Enable logging to syslog for all camera services:

```ini
[camera]
logs: syslog
```

Logs are available in `/var/log/messages`.

### RTSP Streaming

Enable RTSP streaming (paxx12 stack only):

```ini
[camera]
rtsp: true
```

RTSP streams will be available at:
- Internal camera: `rtsp://<printer-ip>:8554/stream`
- USB camera: `rtsp://<printer-ip>:8555/stream`

### USB Camera Configuration

Enable USB camera support (paxx12 stack only):

```ini
[camera]
usb: true
```

When enabled, USB cameras are accessible at `http://<printer-ip>/webcam2/`.

After any configuration changes, reboot the printer for changes to take effect.

## Timelapse Support

Fluidd timelapse plugin is included (no settings support).
