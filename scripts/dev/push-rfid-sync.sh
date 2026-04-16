#!/usr/bin/env bash
#
# Push RFID sync files to a running U1.
#
# Usage:
#   ./scripts/dev/push-rfid-sync.sh [user@ip]
#
# Default target: root@192.168.2.242
# Requires SSH key auth (run ssh-copy-id root@<ip> first).
#
# Examples:
#   ./scripts/dev/push-rfid-sync.sh
#   ./scripts/dev/push-rfid-sync.sh root@192.168.2.242
#
# This pushes:
#   1. Expanded OpenRFID webhook templates
#   2. Patched filament_detect.py (applies patch in-place)
#   3. RFID Spools web app (nginx config + HTML)
#   4. Spoolman fields setup script
#
# After push, restarts OpenRFID and nginx.

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

SSH_HOST="${1:-root@192.168.2.242}"
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

ssh_cmd() {
  ssh $SSH_OPTS "$SSH_HOST" "$@"
}

scp_cmd() {
  scp $SSH_OPTS "$@"
}

echo ">> Target: $SSH_HOST"

# ── 1. Push OpenRFID webhook templates ──
echo ">> Pushing OpenRFID webhook templates..."
OPENRFID_SRC="$REPO_DIR/overlays/firmware-extended/64-app-openrfid/root/usr/local/share/openrfid/extended"
scp_cmd \
  "$OPENRFID_SRC/openrfid_u1_vendor.cfg" \
  "$OPENRFID_SRC/openrfid_u1_generic.cfg" \
  "$SSH_HOST:/usr/local/share/openrfid/extended/"

# ── 1b. Apply OpenRFID TigerTag TD + bed temp patch ──
echo ">> Applying OpenRFID TigerTag TD patch..."
OPENRFID_TD_PATCH="$REPO_DIR/overlays/firmware-extended/64-app-openrfid/patches/usr/local/share/openrfid/03-add-tigertag-td-and-bed-temp.patch"

if ssh_cmd "grep -q 'self.td' /usr/local/share/openrfid/filament/generic.py 2>/dev/null"; then
  echo "   TD patch already applied, skipping."
else
  # Reverse any partial application first
  ssh_cmd "cd /usr/local/share/openrfid && patch -R -p1 --forward < /tmp/openrfid_td.patch 2>/dev/null" || true
  # Strip Windows \r line endings before sending to Linux
  tr -d '\r' < "$OPENRFID_TD_PATCH" | ssh_cmd "cat > /tmp/openrfid_td.patch"
  ssh_cmd "cd /usr/local/share/openrfid && patch -p1 --forward < /tmp/openrfid_td.patch && rm /tmp/openrfid_td.patch"
  echo "   TD patch applied."
fi

# ── 2. Patch filament_detect/set to accept extended fields ──
echo ">> Patching filament_detect/set handler..."
REMOTE_PY="/home/lava/klipper/klippy/extras/filament_detect.py"

# Check if already patched (look for DRYING_TEMP which is new)
if ssh_cmd "grep -q 'DRYING_TEMP' $REMOTE_PY 2>/dev/null"; then
  echo "   Extended fields already present, skipping."
else
  # The printer already has a basic /set handler but without DIAMETER, WEIGHT,
  # DRYING_TEMP, DRYING_TIME, MF_DATE, TD fields.  Inject them just before the
  # "unsupported fields" guard.  We scp a small Python patcher to avoid quoting hell.
  PATCHER=$(mktemp)
  cat > "$PATCHER" << 'PYEOF'
import sys
path = sys.argv[1]
with open(path) as f:
    code = f.read()
marker = "            if params:\n                raise web_request.error"
if marker not in code:
    print("ERROR: cannot find unsupported-fields guard", file=sys.stderr)
    sys.exit(1)
inject = (
    "            if 'DIAMETER' in params:\n"
    "                filament_info['DIAMETER'] = int(params.pop('DIAMETER'))\n"
    "            if 'WEIGHT' in params:\n"
    "                filament_info['WEIGHT'] = int(params.pop('WEIGHT'))\n"
    "            if 'DRYING_TEMP' in params:\n"
    "                filament_info['DRYING_TEMP'] = int(params.pop('DRYING_TEMP'))\n"
    "            if 'DRYING_TIME' in params:\n"
    "                filament_info['DRYING_TIME'] = int(params.pop('DRYING_TIME'))\n"
    "            if 'MF_DATE' in params:\n"
    "                filament_info['MF_DATE'] = str(params.pop('MF_DATE'))\n"
    "            if 'TD' in params:\n"
    "                filament_info['TD'] = float(params.pop('TD'))\n"
    "\n"
)
code = code.replace(marker, inject + marker, 1)
with open(path, 'w') as f:
    f.write(code)
print("Extended fields injected successfully.")
PYEOF
  scp_cmd "$PATCHER" "$SSH_HOST:/tmp/_patch_fd.py"
  rm -f "$PATCHER"
  ssh_cmd "python3 /tmp/_patch_fd.py $REMOTE_PY && rm /tmp/_patch_fd.py"
  echo "   Done."
fi

# ── 3. Push RFID Spools web app ──
echo ">> Pushing RFID Spools web app..."
RFID_SPOOLS_ROOT="$REPO_DIR/overlays/firmware-extended/68-app-rfid-spools/root"

# Push all files from the overlay root tree
tar -cf - -C "$RFID_SPOOLS_ROOT" . |
  ssh_cmd tar -C / -xf -

# Ensure nginx fluidd.d directory exists and reload
ssh_cmd "mkdir -p /etc/nginx/fluidd.d"

# ── 4. Push Spoolman setup script ──
echo ">> Setting permissions..."
ssh_cmd "chmod +x /usr/local/bin/setup-spoolman-fields.sh"

# ── 5. Restart services ──
echo ">> Restarting firmware-config (new actions YAML)..."
ssh_cmd "/etc/init.d/S99firmware-config restart" || ssh_cmd "killall -HUP firmware-config.py" || true

echo ">> Restarting Klipper (to load patched filament_detect.py)..."
ssh_cmd "/etc/init.d/S60klipper restart" || true
sleep 2

echo ">> Restarting OpenRFID..."
ssh_cmd "/etc/init.d/S99openrfid restart" || true

echo ">> Reloading nginx..."
ssh_cmd "nginx -t && nginx -s reload" || echo "   nginx reload failed (check config)"

echo ""
echo ">> Done! RFID Spools web app available at:"
echo "   http://${SSH_HOST#*@}/rfid-spools/"
echo ""
echo ">> Enter your Spoolman URL in the web UI config panel."
echo ">> The proxy is dynamic — no server-side config needed."
echo ""
echo ">> To set up Spoolman custom fields, use the button in the"
echo "   web UI or run on the U1:"
echo "   setup-spoolman-fields.sh http://<spoolman-host>:7912"
