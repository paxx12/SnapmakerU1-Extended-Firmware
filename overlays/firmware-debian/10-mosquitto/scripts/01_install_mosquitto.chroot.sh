#!/bin/bash

set -e

echo ">> Enabling mosquitto service..."
systemctl enable mosquitto

echo ">> Mosquitto installation complete"
