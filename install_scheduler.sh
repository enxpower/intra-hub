#!/bin/bash
# INTRA-HUB v1.0 - Scheduler Installation
# Installs daily sync job using systemd timer

set -e

if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo"
    exit 1
fi

echo "=== Installing INTRA-HUB Scheduler ==="

# Create systemd service file
cat > /etc/systemd/system/intra-hub-sync.service << 'EOF'
[Unit]
Description=INTRA-HUB Daily Sync
After=network.target

[Service]
Type=oneshot
User=www-data
Group=www-data
WorkingDirectory=/opt/intra-hub
Environment="PATH=/opt/intra-hub/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/opt/intra-hub/venv/bin/python /opt/intra-hub/sync/main.py
StandardOutput=append:/opt/intra-hub/logs/scheduler.log
StandardError=append:/opt/intra-hub/logs/scheduler.log
EOF

# Create systemd timer file
cat > /etc/systemd/system/intra-hub-sync.timer << 'EOF'
[Unit]
Description=INTRA-HUB Daily Sync Timer
Requires=intra-hub-sync.service

[Timer]
# Run daily at 2:00 AM
OnCalendar=daily
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload

# Enable and start timer
echo "Enabling timer..."
systemctl enable intra-hub-sync.timer
systemctl start intra-hub-sync.timer

# Show status
echo ""
echo "=== Installation Complete ==="
echo ""
systemctl status intra-hub-sync.timer --no-pager
echo ""
echo "Timer Schedule:"
systemctl list-timers intra-hub-sync.timer --no-pager
echo ""
echo "Manual trigger: sudo systemctl start intra-hub-sync.service"
echo "View logs: sudo journalctl -u intra-hub-sync.service -f"
echo ""
