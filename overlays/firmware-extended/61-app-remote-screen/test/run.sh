#!/usr/bin/env bash

ROOT_DIR="$(dirname "$(realpath "$0")")/.."

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <u1.home> [fb-http-server-args...]"
    exit 1
fi

HOST="$1"
shift

scp -r "$ROOT_DIR/root/." "root@$HOST:/"
ssh -t "root@$HOST" /etc/init.d/S99fb-http stop
ssh -t "root@$HOST" /usr/local/bin/fb-http-server.py --html "/usr/local/share/fb-http-server/index.html" "$@"
