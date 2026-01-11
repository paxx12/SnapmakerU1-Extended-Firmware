#!/usr/bin/env python3

import socket
import argparse
import time
import json
from urllib.parse import urlparse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

HTML_INDEX = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Detection Visualization</title>
<style>
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}
html, body {
    width: 100%;
    height: 100%;
    background: #1a1a1a;
    overflow: hidden;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
}
#container {
    position: relative;
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}
#canvas {
    max-width: 100%;
    max-height: 100%;
    background: #000;
    display: block;
}
#status {
    position: fixed;
    top: 10px;
    left: 10px;
    color: #fff;
    font-size: 14px;
    background: rgba(0,0,0,0.7);
    padding: 8px 12px;
    border-radius: 4px;
    z-index: 100;
}
#detections {
    position: fixed;
    top: 10px;
    right: 10px;
    color: #fff;
    font-size: 12px;
    background: rgba(0,0,0,0.7);
    padding: 8px 12px;
    border-radius: 4px;
    z-index: 100;
    max-width: 300px;
    max-height: 80%;
    overflow-y: auto;
}
.detection-item {
    margin: 4px 0;
    padding: 4px;
    border-left: 3px solid;
}
.detection-label {
    font-weight: bold;
}
#controls {
    position: fixed;
    bottom: 10px;
    left: 10px;
    z-index: 100;
}
#toggleBtn {
    padding: 10px 20px;
    font-size: 14px;
    font-weight: bold;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
}
#toggleBtn.running {
    background: #52BE80;
    color: #000;
}
#toggleBtn.stopped {
    background: #E74C3C;
    color: #fff;
}
#toggleBtn:hover {
    opacity: 0.8;
}
</style>
</head>
<body>
<div id="container">
    <canvas id="canvas"></canvas>
</div>
<div id="status">Loading...</div>
<div id="detections"></div>
<div id="controls">
    <button id="toggleBtn" class="running">Stop Detection</button>
</div>
<script>
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const statusEl = document.getElementById('status');
const detectionsEl = document.getElementById('detections');
const toggleBtn = document.getElementById('toggleBtn');
let updateInterval = null;
let frameCount = 0;
let lastTime = Date.now();
let fps = 0;
let isRunning = true;

const colors = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
    '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52BE80'
];

function getColorForClass(className) {
    const hash = className.split('').reduce((acc, char) => {
        return char.charCodeAt(0) + ((acc << 5) - acc);
    }, 0);
    return colors[Math.abs(hash) % colors.length];
}

async function updateFrame() {
    try {
        const timestamp = Date.now();
        const response = await fetch(`/frame?t=${timestamp}`);
        if (!response.ok) throw new Error('Failed to fetch frame');

        const data = await response.json();
        const image = new Image();

        image.onload = () => {
            canvas.width = image.width;
            canvas.height = image.height;
            ctx.drawImage(image, 0, 0);

            if (data.detections && Object.keys(data.detections).length > 0) {
                drawDetections(data.detections);
                displayDetectionInfo(data.detections, data.stats);
            } else {
                detectionsEl.innerHTML = '<div style="opacity:0.6;">No detections</div>';
            }

            frameCount++;
            const now = Date.now();
            if (now - lastTime >= 1000) {
                fps = frameCount;
                frameCount = 0;
                lastTime = now;
            }
            const statusText = isRunning ? 'Running' : 'Stopped';
            let statusStr = `${statusText} | FPS: ${fps} | ${image.width}x${image.height}`;
            if (data.stats) {
                statusStr += ` | Capture: ${(data.stats.capture_time * 1000).toFixed(1)}ms`;
            }
            statusEl.textContent = statusStr;
        };

        image.src = 'data:image/jpeg;base64,' + data.image;

    } catch (error) {
        statusEl.textContent = `Error: ${error.message}`;
        console.error('Update error:', error);
    }
}

function drawDetections(detections) {
    let totalBoxes = 0;
    for (const [socketName, socketDetections] of Object.entries(detections)) {
        for (const [className, objects] of Object.entries(socketDetections)) {
            const color = getColorForClass(className);
            ctx.strokeStyle = color;
            ctx.lineWidth = 3;
            ctx.font = '16px monospace';
            ctx.fillStyle = color;

            objects.forEach(obj => {
                const x = obj.x;
                const y = obj.y;
                const w = obj.w;
                const h = obj.h;

                ctx.strokeRect(x, y, w, h);

                const label = `${className} ${(obj.confidence * 100).toFixed(1)}%`;
                const textMetrics = ctx.measureText(label);
                const textHeight = 20;

                ctx.fillStyle = color;
                ctx.fillRect(x, y - textHeight, textMetrics.width + 8, textHeight);

                ctx.fillStyle = '#000';
                ctx.fillText(label, x + 4, y - 4);

                totalBoxes++;
            });
        }
    }
}

function displayDetectionInfo(detections, stats) {
    let html = '';
    if (stats && stats.processing_times) {
        html += '<div style="margin-bottom: 12px; padding: 8px; background: rgba(255,255,255,0.1); border-radius: 4px;">';
        html += '<div style="font-weight: bold; margin-bottom: 4px;">Processing Times</div>';
        for (const [socketName, procTime] of Object.entries(stats.processing_times)) {
            html += `<div style="font-size: 11px;">${socketName}: ${(procTime * 1000).toFixed(1)}ms</div>`;
        }
        html += '</div>';
    }
    for (const [socketName, socketDetections] of Object.entries(detections)) {
        html += `<div style="margin-top: 8px; padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.2);"><strong>${socketName}</strong></div>`;
        for (const [className, objects] of Object.entries(socketDetections)) {
            if (objects.length === 0) continue;
            const color = getColorForClass(className);
            const count = objects.length;
            const avgConf = objects.reduce((sum, obj) => sum + obj.confidence, 0) / count;

            html += `
<div class="detection-item" style="border-color: ${color};">
    <div class="detection-label">${className}</div>
    <div>Count: ${count}</div>
    <div>Avg Conf: ${(avgConf * 100).toFixed(1)}%</div>
</div>
`;
        }
    }
    detectionsEl.innerHTML = html;
}

function startDetection() {
    if (updateInterval) return;
    isRunning = true;
    updateInterval = setInterval(updateFrame, 1000);
    toggleBtn.textContent = 'Stop Detection';
    toggleBtn.className = 'running';
    updateFrame();
}

function stopDetection() {
    if (!updateInterval) return;
    isRunning = false;
    clearInterval(updateInterval);
    updateInterval = null;
    toggleBtn.textContent = 'Start Detection';
    toggleBtn.className = 'stopped';
    statusEl.textContent = 'Stopped';
}

toggleBtn.addEventListener('click', () => {
    if (isRunning) {
        stopDetection();
    } else {
        startDetection();
    }
});

startDetection();
</script>
</body>
</html>
"""

def log(msg):
    ts = time.strftime('%H:%M:%S')
    print(f"[{ts}] {msg}", flush=True)

def read_socket(sock_path, chunk_size=65536):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    sock.connect(sock_path)
    try:
        chunks = []
        while True:
            chunk = sock.recv(chunk_size)
            if not chunk:
                break
            chunks.append(chunk)
        return b''.join(chunks)
    finally:
        sock.close()

def send_detect_request(sock_path, image_path):
    if not sock_path:
        return {"error": "Detection socket not configured"}
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(sock_path)
        request = {"image": image_path}
        sock.sendall(json.dumps(request).encode('utf-8'))
        sock.shutdown(socket.SHUT_WR)
        chunks = []
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
        sock.close()
        response = b''.join(chunks).decode('utf-8')
        return json.loads(response)
    except Exception as e:
        log(f"Detection request failed: {e}")
        return {"error": str(e)}

class DetectHTTPHandler(BaseHTTPRequestHandler):
    jpeg_sock = None
    detect_socks = []
    temp_image_path = "/tmp/detect-http-frame.jpg"

    def log_message(self, format, *args):
        log(f"HTTP {self.address_string()} - {format % args}")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/':
            self.handle_index()
        elif path == '/frame':
            self.handle_frame()
        else:
            self.send_error(404, 'Not Found')

    def send_html(self, html):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(html.encode('utf-8')))
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def send_json(self, data):
        json_str = json.dumps(data)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(json_str))
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.end_headers()
        self.wfile.write(json_str.encode('utf-8'))

    def handle_index(self):
        self.send_html(HTML_INDEX)

    def handle_frame(self):
        if not self.jpeg_sock:
            self.send_error(503, 'JPEG socket not available')
            return

        try:
            import base64
            import os
            start_time = time.time()
            jpeg_data = read_socket(self.jpeg_sock)
            capture_time = time.time() - start_time

            with open(self.temp_image_path, 'wb') as f:
                f.write(jpeg_data)

            detections_by_socket = {}
            processing_times = {}
            for detect_sock in self.detect_socks:
                sock_basename = os.path.basename(detect_sock).replace('.sock', '')
                proc_start = time.time()
                detect_result = send_detect_request(detect_sock, self.temp_image_path)
                proc_time = time.time() - proc_start
                processing_times[sock_basename] = proc_time
                if "error" not in detect_result:
                    detections_by_socket[sock_basename] = detect_result.get("detections", {})

            image_b64 = base64.b64encode(jpeg_data).decode('utf-8')
            response = {
                "image": image_b64,
                "detections": detections_by_socket,
                "stats": {
                    "capture_time": capture_time,
                    "processing_times": processing_times
                },
                "timestamp": time.time()
            }

            self.send_json(response)

        except Exception as e:
            log(f"Frame error: {e}")
            self.send_error(500, str(e))

def main():
    parser = argparse.ArgumentParser(description='AI Detection Visualization Server')
    parser.add_argument('-p', '--port', type=int, default=8091, help='HTTP port')
    parser.add_argument('--bind', default='0.0.0.0', help='Bind address')
    parser.add_argument('--jpeg-sock', required=True, help='JPEG snapshot socket')
    parser.add_argument('--detect-sock', action='append', help='Detection socket path (can be used multiple times)')
    args = parser.parse_args()

    DetectHTTPHandler.jpeg_sock = args.jpeg_sock
    DetectHTTPHandler.detect_socks = args.detect_sock or []

    server = ThreadingHTTPServer((args.bind, args.port), DetectHTTPHandler)
    log(f"AI Visualization Server running on http://{args.bind}:{args.port}")
    log(f"JPEG socket: {args.jpeg_sock}")
    for i, sock in enumerate(DetectHTTPHandler.detect_socks):
        log(f"Detection socket {i+1}: {sock}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("Shutting down...")

if __name__ == '__main__':
    main()
