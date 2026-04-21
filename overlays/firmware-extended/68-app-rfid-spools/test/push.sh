#!/usr/bin/env bash
#
# Push rfid-spools overlay files to the printer and restart the service.
#
# Usage: ./push.sh root@<printer-ip>
#
# SSH key setup (avoids password prompts):
#   1. Generate a key (if you don't have one):
#        ssh-keygen -t ed25519
#   2. Copy it to the printer:
#        ssh-copy-id -o StrictHostKeyChecking=no root@192.168.2.242
#      (default password: snapmaker)
#   3. Verify passwordless login:
#        ssh root@192.168.2.242 echo ok
#

set -e

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <user@host>"
    echo "Example: $0 root@192.168.2.242"
    exit 1
fi

# Prepend root@ if no user specified
HOST="$1"
if [[ "$HOST" != *@* ]]; then
    HOST="root@$HOST"
fi
OVERLAY_DIR="$(dirname "$(realpath "$0")")/../root"
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

TMPDIR=$(mktemp -d)
ARCHIVE=$(mktemp /tmp/rfid-push-XXXXXX.tar.gz)
trap 'rm -rf "$TMPDIR" "$ARCHIVE"' EXIT

echo ">> Packing archive (stripping CRLF)..."
cp -r "$OVERLAY_DIR"/. "$TMPDIR"/
find "$TMPDIR" -type f \( -name '*.sh' -o -name '*.py' -o -name '*.conf' -o -name '*.cfg' \
    -o -name 'S99*' -o -name '*.html' -o -name '*.js' -o -name '*.css' \) \
    -exec sed -i 's/\r$//' {} +
tar -czf "$ARCHIVE" -C "$TMPDIR" .

echo ">> Uploading to $HOST..."
scp $SSH_OPTS "$ARCHIVE" "$HOST:/tmp/rfid-push.tar.gz"

echo ">> Deploying on $HOST..."
ssh $SSH_OPTS "$HOST" '
  set -e
  rm -rf /usr/local/share/rfid-spools/html /usr/local/bin/rfid-spools-api.py
  tar -C / -xzf /tmp/rfid-push.tar.gz
  rm -f /tmp/rfid-push.tar.gz
  chmod -R a+rX /usr/local/share/rfid-spools/html/
  chmod 755 /etc/init.d/S99rfid-spools /etc/init.d/S99openrfid /usr/local/bin/rfid-spools-api.py
  # Clear Python bytecode caches for any modified openrfid files so Python reloads them
  rm -f /usr/local/share/openrfid/filament/__pycache__/generic.cpython-*.pyc
  rm -f /usr/local/share/openrfid/tag/tigertag/__pycache__/processor.cpython-*.pyc
  /etc/init.d/S99rfid-spools restart
  /etc/init.d/S99openrfid restart
  nginx -s reload
'

echo ">> Deployed files:"
ssh $SSH_OPTS "$HOST" "find /usr/local/share/rfid-spools/html/ -type f"

echo ">> Done. Access at http://${HOST#*@}/spools/"
