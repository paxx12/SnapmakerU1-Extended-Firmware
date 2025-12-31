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

You need to add USB camera in Fluidd. Use the following
settings for the best performance:

<img src="images/usb_cam.png" alt="Fluidd USB camera" width="300"/>

## Switch to Snapmaker's Original Camera Stack

By default, the extended firmware uses a custom hardware-accelerated camera stack (paxx12).
If you prefer to use Snapmaker's original camera stack instead, edit `/home/lava/printer_data/config/extended/extended.cfg`:

```ini
[camera]
# stack: paxx12
stack: snapmaker
logs: syslog
```

Then reboot the printer.

Note: Only one camera stack can be operational at a time. See [Extended Configuration](extended_config.md) for details.

## Camera Logging

Camera service logging to syslog is controlled by the `logs` setting in `/home/lava/printer_data/config/extended/extended.cfg`:

```ini
[camera]
stack: paxx12
logs: syslog
```

This enables the `--syslog` flag for all camera-related services. Logs are available in `/var/log/messages`. See [Extended Configuration](extended_config.md) for details.

## AI detection support

Currently the `stack: paxx12` does not support AI detection features.
Those will be implemented at a later time.

You can revert back to `stack: snapmaker` to have those back, at the
expense of camera support. You will also have to modify `02_internal_camera.cfg` to be:

```toml
[webcam case]
service: mjpegstreamer-adaptive
stream_url: /camera/capture.jpg
snapshot_url: /camera/capture.jpg
target_fps: 2
target_fps_idle: 1
aspect_ratio: 16:9
```

## Timelapse Support

Fluidd timelapse plugin is included (no settings support).

Note: Time-lapses are not available via mobile app in cloud mode.
