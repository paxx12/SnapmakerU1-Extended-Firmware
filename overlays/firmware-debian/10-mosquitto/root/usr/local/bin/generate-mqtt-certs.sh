#!/bin/bash

CERT_DIR="/home/lava/printer_data/certs"
MQTT_DIR="/home/lava/printer_data/mqtt"
CNF_DIR="/usr/share/mqtt-certs"

CA_KEY="$CERT_DIR/mqtt_ca.key"
CA_CERT="$CERT_DIR/mqtt_ca.crt"
SERVER_KEY="$CERT_DIR/mqtt_server.key"
SERVER_CERT="$CERT_DIR/mqtt_server.crt"
SERVER_CSR="$CERT_DIR/mqtt_server.csr"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

mkdir -p "$CERT_DIR" "$MQTT_DIR"
touch "$MQTT_DIR/users.conf"

if [ -f "$CA_KEY" ] && [ -f "$CA_CERT" ]; then
    log "CA certificate already exists, skipping generation"
else
    log "Generating CA certificate"
    openssl genrsa -out "$CA_KEY" 2048 2>&1
    openssl req -x509 -new -nodes -key "$CA_KEY" -sha256 -days 3650 -out "$CA_CERT" -config "$CNF_DIR/ca.cnf" 2>&1
fi

if [ -f "$SERVER_KEY" ] && [ -f "$SERVER_CERT" ]; then
    log "Server certificate already exists, skipping generation"
else
    log "Generating server certificate"
    openssl genrsa -out "$SERVER_KEY" 2048 2>&1
    openssl req -new -key "$SERVER_KEY" -out "$SERVER_CSR" -config "$CNF_DIR/server.cnf" 2>&1
    openssl x509 -req -in "$SERVER_CSR" -CA "$CA_CERT" -CAkey "$CA_KEY" -CAcreateserial -out "$SERVER_CERT" -days 3650 -sha256 -extfile "$CNF_DIR/server_ext.cnf" 2>&1
    rm -f "$SERVER_CSR"
fi

chown -R lava:lava /home/lava/printer_data
chmod 755 "$CERT_DIR"
chmod 644 "$CERT_DIR"/*

log "MQTT certificates ready"
