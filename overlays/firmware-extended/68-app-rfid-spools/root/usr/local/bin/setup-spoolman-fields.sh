#!/bin/sh
#
# Setup custom extra fields in Spoolman for RFID spool sync.
# Run once against your Spoolman instance:
#   setup-spoolman-fields.sh http://spoolman-host:7912
#
# Idempotent: re-running will get 409 Conflict for existing fields (harmless).

set -e

SPOOLMAN_URL="${1:-}"

if [ -z "$SPOOLMAN_URL" ]; then
    echo "Usage: $0 <spoolman-url>"
    echo "Example: $0 http://192.168.1.100:7912"
    exit 1
fi

# Strip trailing slash
SPOOLMAN_URL="${SPOOLMAN_URL%/}"

echo "Setting up Spoolman custom fields at $SPOOLMAN_URL ..."

create_field() {
    entity="$1"
    key="$2"
    payload="$3"

    printf "  Creating %s field '%s'... " "$entity" "$key"
    code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$SPOOLMAN_URL/api/v1/field/$entity/$key" \
        -H 'Content-Type: application/json' \
        -d "$payload")

    case "$code" in
        200|201) echo "OK" ;;
        409)     echo "already exists" ;;
        *)       echo "FAILED (HTTP $code)" ;;
    esac
}

# Filament-level extra fields
create_field filament td \
    '{"name":"Transmission Distance","field_type":"float","unit":"mm","order":1}'

create_field filament subtype \
    '{"name":"Subtype","field_type":"text","order":2}'

create_field filament hotend_min_temp \
    '{"name":"Min Hotend Temp","field_type":"integer","unit":"°C","order":3}'

create_field filament drying_temp \
    '{"name":"Drying Temperature","field_type":"integer","unit":"°C","order":4}'

create_field filament drying_time \
    '{"name":"Drying Time","field_type":"integer","unit":"h","order":5}'

create_field filament mfg_date \
    '{"name":"Manufacturing Date","field_type":"text","order":6}'

# Spool-level extra fields
create_field spool rfid_uid \
    '{"name":"RFID Tag UID","field_type":"text","order":1}'

create_field spool tigertag_product_id \
    '{"name":"TigerTag Product ID","field_type":"text","order":2}'

echo "Done."
