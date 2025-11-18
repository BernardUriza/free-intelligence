#!/bin/bash
# Health check script for Free Intelligence container
# Verifies backend API is responding correctly

# Check backend health endpoint
curl -f http://localhost:7001/health || exit 1

# Check if HDF5 storage is accessible
if [ ! -f /app/storage/corpus.h5 ]; then
    echo "Warning: corpus.h5 not found, but service is running"
fi

# Check if logs directory is writable
touch /app/logs/health.check 2>/dev/null || {
    echo "Warning: Cannot write to logs directory"
    exit 1
}
rm -f /app/logs/health.check

echo "Health check passed"
exit 0
