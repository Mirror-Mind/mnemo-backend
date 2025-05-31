#!/bin/bash
set -e

# Create necessary directories with proper permissions
mkdir -p /home/appuser/.mem0 /app/.mem0
chmod -R 755 /home/appuser/.mem0 /app/.mem0

# Handle logs directory more carefully
mkdir -p /app/logs

# Try to set permissions on logs directory, but don't fail if it's not possible
# (this can happen when logs is mounted as a volume)
if [ -w /app/logs ]; then
    chmod -R 755 /app/logs 2>/dev/null || echo "Warning: Could not change permissions on /app/logs (likely mounted volume)"
    chown -R appuser:appuser /app/logs 2>/dev/null || echo "Warning: Could not change ownership of /app/logs (likely mounted volume)"
else
    echo "Warning: /app/logs is not writable, skipping permission changes"
fi

# Export environment variables for mem0
export MEM0_DIR="/app/.mem0"
export HOME="/home/appuser"
export TMPDIR="/tmp"

# Execute the main command
exec "$@" 