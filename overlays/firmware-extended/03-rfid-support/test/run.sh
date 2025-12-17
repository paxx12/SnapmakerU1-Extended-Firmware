#!/bin/bash

ROOT_DIR="$(dirname "$(realpath "$0")")/.."

scp "$ROOT_DIR/root/home/lava/klipper/klippy/extras/fm175xx_reader.py" root@u1eth.home:/home/lava/klipper/klippy/extras/
scp "$ROOT_DIR/../../scripts/dev/run-klipper.sh" "$ROOT_DIR/test/test_printer.cfg" root@u1eth.home:/tmp/
ssh -t root@u1eth.home /tmp/run-klipper.sh /tmp/test_printer.cfg
