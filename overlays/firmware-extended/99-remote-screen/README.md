# Remote Screen Access

This overlay provides web-based remote screen access with touch control for the Snapmaker U1.

## Architecture

```text
                    ┌───────────────────────────┐
                    │      Web Browser          │
                    │   (User's Computer)       │
                    └─────────────┬─────────────┘
                                  │ HTTPS/HTTP
                                  │
                    ┌─────────────▼─────────────┐
                    │          nginx            │
                    │  ┌─────────────────────┐  │
                    │  │  Static Files       │  │
                    │  │  /screen/*          │  │
                    │  └─────────────────────┘  │
                    │  ┌─────────────────────┐  │
                    │  │  WebSocket Proxy    │  │
                    │  │  /screen/websockify │  │
                    │  │  → unix socket      │  │
                    │  └─────────────────────┘  │
                    └──┬───────────────────┬────┘
                       │                   │
        Static Files   │                   │ Unix Socket
                       │                   │ /var/run/websockify.sock
            ┌──────────▼─────────┐    ┌────▼───────────────┐
            │       noVNC        │    │    websockify      │
            │   (HTML/JS/CSS)    │    │    (WS ↔ TCP)      │
            └────────────────────┘    └────┬───────────────┘
                                           │ TCP (VNC Protocol)
                                           │ 127.0.0.1:5900
                              ┌────────────▼───────────────┐
                              │  framebuffer-vncserver     │
                              │  - Reads /dev/fb0          │
                              │  - Injects touch events    │
                              └────┬─────────────────┬─────┘
                                   │                 │
                    ┌──────────────▼───┐      ┌──────▼──────────────┐
                    │   Framebuffer    │      │   Touch Screen      │
                    │    /dev/fb0      │      │   /dev/input/...    │
                    │    (480x320)     │      │   event*            │
                    └──────────────────┘      └─────────────────────┘
```

## Components

### framebuffer-vncserver

- **Purpose**: VNC server for embedded devices with framebuffer display
- **Function**:
  - Reads screen content from `/dev/fb0`
  - Listens on configurable interface (default `127.0.0.1:5900`, VNC protocol)
  - Injects touch events to `/dev/input/by-path/platform-ffa10000.i2c-event`
- **Source**: <https://github.com/ponty/framebuffer-vncserver>
- **Patches Applied**:
  - `multitouch-support.patch`: Adds multi-touch support using ABS_MT_POSITION_X/Y events
  - `framebuffer-vncserver-localhost.patch`:
    - Binds to localhost (127.0.0.1) by default for security
    - Adds `-L <interface>` option to specify listen interface
    - Use `-L 0.0.0.0` to listen on all interfaces if needed

### noVNC

- **Purpose**: HTML5/JavaScript VNC client
- **Function**:
  - Provides web-based VNC viewer
  - Converts user input to VNC protocol over WebSocket
- **Location**: `/home/lava/novnc`
- **Version**: 1.7.0-beta
- **Source**: <https://github.com/novnc/noVNC>

### websockify

- **Purpose**: WebSocket to TCP proxy
- **Function**:
  - Bridges WebSocket connections from browser to VNC TCP socket
  - Listens on Unix socket `/var/run/websockify.sock` (WebSocket)
  - Proxies to `127.0.0.1:5900` (VNC)
- **Source**: <https://github.com/novnc/websockify>

### nginx

- **Purpose**: Web server and reverse proxy (stock component)
- **Function**:
  - Serves noVNC static files at `/screen/`
  - Proxies WebSocket connections from `/screen/websockify` to Unix socket `/var/run/websockify.sock`

## Data Flow

1. **Display Output**: Framebuffer → framebuffer-vncserver → websockify → nginx → Browser
2. **Touch Input**: Browser → nginx → websockify → framebuffer-vncserver → Touch device

## Security

All VNC components use localhost-only communication:

- **framebuffer-vncserver**: Configurable interface (default `127.0.0.1:5900`)
- **websockify**: Unix domain socket `/var/run/websockify.sock` (mode 0660, owner `lava:www-data`)
- **nginx**: Public endpoint at `:80/screen/*` (reverse proxy)

This ensures VNC traffic is only accessible through the nginx reverse proxy, preventing direct network access to the VNC server. The Unix socket approach eliminates TCP port exposure entirely for the WebSocket proxy.

## Patches

### multitouch-support.patch

Adds multi-touch support to framebuffer-vncserver for the Snapmaker U1's capacitive touchscreen.

**Changes**:

- Reads multi-touch coordinates from `ABS_MT_POSITION_X` and `ABS_MT_POSITION_Y` events
- Maps browser touch coordinates to the physical touchscreen coordinate space
- Enables proper touch interaction through the web interface

**Reason**: The original framebuffer-vncserver only supported single-touch devices using `ABS_X`/`ABS_Y` events. The Snapmaker U1's touchscreen uses the modern multi-touch protocol with `ABS_MT_*` events.

### framebuffer-vncserver-localhost.patch

Adds localhost binding and configurable listen interface to framebuffer-vncserver.

**Changes**:

- Sets default listen interface to `127.0.0.1` (localhost only)
- Adds `-L <interface>` command-line option to specify listen interface
- Supports `0.0.0.0` to listen on all interfaces if needed

**Reason**: Security. The original framebuffer-vncserver binds to all interfaces (`0.0.0.0:5900`), exposing the VNC server to the network without authentication. Since we use websockify and nginx as proxies, the VNC server should only accept local connections.

## Access

Once configured, the remote screen is accessible at:

```text
http://<printer-ip>/screen/vnc.html
```

Or with auto-connect parameters:

```text
http://<printer-ip>/screen/vnc.html?host=<printer-ip>&path=websockify&autoconnect=true
```
