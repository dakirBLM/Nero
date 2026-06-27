#!/bin/bash

# NERO Platform - Blocked IPs Auto-Export Script
# This script exports blocked IP data to blocked_ips.txt
# Can be run as a cron job for regular updates

# Settings
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
MANAGE_PY="$PROJECT_DIR/manage.py"
BLOCKED_IPS_FILE="$PROJECT_DIR/blocked_ips.txt"
TEMP_FILE="/tmp/nero_blocked_ips_temp.txt"

# Check if manage.py exists
if [ ! -f "$MANAGE_PY" ]; then
    echo "Error: manage.py not found at $MANAGE_PY"
    exit 1
fi

# Export blocked IPs to temporary file
echo "# NERO Platform - Blocked IP Addresses" > "$TEMP_FILE"
echo "# Auto-generated on: $(date)" >> "$TEMP_FILE"
echo "# Total blocked IPs found: $(python3 "$MANAGE_PY" shell -c "from accounts.models import BlockedIPRecord; print(BlockedIPRecord.objects.count())")" >> "$TEMP_FILE"
echo "#" >> "$TEMP_FILE"
echo "# Legend:" >> "$TEMP_FILE"
echo "# PERMANENT = Permanently blocked (3+ violations)" >> "$TEMP_FILE"
echo "# TEMP = Temporarily blocked (active in cache)" >> "$TEMP_FILE"
echo "# MONITORED = Being tracked (1-2 blocks)" >> "$TEMP_FILE"
echo "#" >> "$TEMP_FILE"
echo "# Management commands:" >> "$TEMP_FILE"
echo "# View all: python3 manage.py view_blocked_ips" >> "$TEMP_FILE"
echo "# Permanent only: python3 manage.py view_blocked_ips --permanent-only" >> "$TEMP_FILE"
echo "# Export JSON: python3 manage.py view_blocked_ips --format json --export-file blocked_ips.json" >> "$TEMP_FILE"
echo "# Unblock IP: python3 manage.py view_blocked_ips --unblock IP_ADDRESS" >> "$TEMP_FILE"
echo "#" >> "$TEMP_FILE"
echo "# ===========================================" >> "$TEMP_FILE"
echo "# BLOCKED IP ADDRESSES" >> "$TEMP_FILE"
echo "# ===========================================" >> "$TEMP_FILE"
echo "" >> "$TEMP_FILE"

# Get CSV data and append
python3 "$MANAGE_PY" view_blocked_ips --format csv >> "$TEMP_FILE" 2>/dev/null

# If export was successful, replace the main file
if [ $? -eq 0 ]; then
    mv "$TEMP_FILE" "$BLOCKED_IPS_FILE"
    echo "✅ Blocked IPs exported successfully to $BLOCKED_IPS_FILE"
    
    # Show summary
    TOTAL_COUNT=$(python3 "$MANAGE_PY" shell -c "from accounts.models import BlockedIPRecord; print(BlockedIPRecord.objects.count())" 2>/dev/null)
    PERMANENT_COUNT=$(python3 "$MANAGE_PY" shell -c "from accounts.models import BlockedIPRecord; print(BlockedIPRecord.objects.filter(is_permanently_blocked=True).count())" 2>/dev/null)
    
    echo "📊 Summary: $TOTAL_COUNT total IPs tracked, $PERMANENT_COUNT permanently blocked"
else
    echo "❌ Error exporting blocked IPs"
    rm -f "$TEMP_FILE"
    exit 1
fi

# If running as cron, log the activity
if [ "$1" == "--cron" ]; then
    echo "$(date): Blocked IPs updated - $TOTAL_COUNT total, $PERMANENT_COUNT permanent" >> "$SCRIPT_DIR/blocked_ips_update.log"
fi