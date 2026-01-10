#!/bin/bash

set -e

OEM_DIR="/oem/printer_data"
SOURCE_DIR="/opt/lava/printer_data"

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "Source directory $SOURCE_DIR does not exist"
  exit 1
fi

if [[ ! -d "$OEM_DIR" ]]; then
  echo "Creating $OEM_DIR from $SOURCE_DIR"
  mkdir -p /oem
  cp -a "$SOURCE_DIR" "$OEM_DIR"
  chown -R lava:lava "$OEM_DIR"
  echo "Printer data initialized successfully"
else
  echo "Printer data already exists at $OEM_DIR"
fi
