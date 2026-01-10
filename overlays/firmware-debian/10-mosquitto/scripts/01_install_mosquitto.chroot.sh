#!/bin/bash

set -e

echo ">> Enabling mqtt-certs service..."
systemctl enable mqtt-certs

echo ">> Enabling mosquitto service..."
systemctl enable mosquitto

echo ">> Mosquitto installation complete"
