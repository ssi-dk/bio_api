#!/bin/bash
set -e

# Fix permissions for volume
if [ -d "/dmx_data" ]; then
    chown -R appuser:appgroup /dmx_data || true
fi

# Drop privileges and run app
exec gosu appuser "$@"
