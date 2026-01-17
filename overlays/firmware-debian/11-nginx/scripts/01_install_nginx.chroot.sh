#!/bin/bash

set -e

echo ">> Enabling nginx service..."
systemctl enable nginx

echo ">> Create /var/log/nginx directory"
mkdir -p /var/log/nginx
chown www-data:www-data /var/log/nginx
chmod 755 /var/log/nginx

echo ">> Remove sites-enabled/default"
rm -f "/etc/nginx/sites-enabled/default"

echo ">> Nginx installation complete"
