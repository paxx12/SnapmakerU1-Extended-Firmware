#!/bin/bash

set -e

echo ">> Set root password..."
echo root:snapmaker | chpasswd
