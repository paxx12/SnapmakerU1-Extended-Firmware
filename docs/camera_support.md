# Camera Support

**Available in: Extended firmware only**

The extended firmware includes hardware-accelerated camera support.

## Features

- Hardware-accelerated camera stack (Rockchip MPP/VPU)
- v4l2-mpp: MIPI CSI and USB camera support
- WebRTC low-latency streaming
- Hot-plug detection for USB cameras
- Ability to select different stream types (WebRTC, MJPEG-adaptive, h264 iframe...)

## Accessing Cameras

### Internal Camera

Access the native camera at:

```shell
http://<printer-ip>/webcam/
```

### USB Camera

Access USB camera at:

```shell
http://<printer-ip>/webcam2/
```

You need to add USB camera to Fluidd. Use the following settings for the best performance:

<img src="images/usb_cam.png" alt="Fluidd USB camera" width="300"/>

Alternatively, you can add USB camera to Moonraker configuration which also makes it available in Fluidd and all other Moonraker clients:

1. In web browser go to Fluidd Configuration editor at `http://<printer-ip>/#/configure`
2. Enter `moonraker` directory and right-click on `03_usb_camera.cfg.disabled` and rename it to `03_usb_camera.cfg`
5. Restart Moonraker service or printer for changes to take effect.

## Change Internal Camera Stream Type

By default the internal "case" camera streams in WebRTC format for low-latency and high-quality video.
Some apps don't support WebRTC (Mobileraker, Homeassistant...), so you may want to switch the default stream type to MJPEG or h264 instead. Or you can have multiple stream types enabled at the same time and client apps can choose the one that works for them.
To do that, simply rename the existing `09_user_camera.cfg.disabled` to `09_user_camera.cfg`. You can do that from Fluidd web interface:

1. In web browser go to Fluidd Configuration editor at `http://<printer-ip>/#/configure`
2. Enter `moonraker` directory, right-click on `09_user_camera.cfg.disabled` and rename it to `09_user_camera.cfg`
    That file contains a section which disables default WebRTC stream:

    ```ini
    [webcam case]
    enabled: false
    ```

    If you prefer to keep the WebRTC stream enabled, simply toggle it to `enabled: true` and modify its settings as needed.

3. Edit any other webcam sections to enable other stream types and configure their settings.
   Refer to [09_user_camera.cfg.disabled](../overlays/camera-v4l2-mpp/root/home/lava/origin_printer_data/config/moonraker/09_user_camera.cfg.disabled) content for examples.
4. Save the changes
5. Restart Moonraker service or printer for changes to take effect.

Refer to official [Moonraker documentation](https://moonraker.readthedocs.io/en/latest/configuration/#webcam) for more details on available webcam settings.

## Switch to Snapmaker's Original Camera Stack

By default, the extended firmware uses a custom hardware-accelerated camera stack.
If you prefer to use Snapmaker's original camera stack instead, create:

```shell
touch /oem/.camera-native
```

Note: Only one camera stack can be operational at a time.

## Enable Camera Logging

To enable syslog logging for camera services (useful for debugging), create:

```shell
touch /oem/.camera-log
```

This will enable the `--syslog` flag for all camera-related services. Logs will then be available in `/var/log/messages`.

## Timelapse Support

Fluidd timelapse plugin is included (no settings support).

Note: Time-lapses are not available via mobile app in cloud mode.
