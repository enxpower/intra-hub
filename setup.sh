#!/bin/bash
# INTRA-HUB v1.0 Setup Script
# This script initializes the directory structure on the server

set -e

echo "=== INTRA-HUB v1.0 Setup ==="

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo"
    exit 1
fi

# Create base directory
BASE_DIR="/opt/intra-hub"
echo "Creating directory structure at $BASE_DIR..."

mkdir -p "$BASE_DIR"/{sync,renderer,data,public,logs,backups}
mkdir -p "$BASE_DIR/public"/{documents,static}
mkdir -p "$BASE_DIR/data"/{cache,metrics}

# Create Python virtual environment
echo "Creating Python virtual environment..."
cd "$BASE_DIR"
python3 -m venv venv

# Activate and install dependencies
source venv/bin/activate
pip install --upgrade pip

# Install required packages
pip install \
    notion-client \
    python-barcode \
    Pillow \
    python-crontab \
    requests

echo "Creating .env template..."
cat > "$BASE_DIR/.env.template" << 'EOF'
# INTRA-HUB v1.0 Environment Configuration
# Copy this to .env and fill in your credentials

NOTION_TOKEN=your_notion_integration_token_here
NOTION_DATABASE_ID=2fa95c292b0e80b0a5b0f6a3d20b64f1

# Optional: Base URL for internal access
BASE_URL=http://intra-hub.internal
EOF

if [ ! -f "$BASE_DIR/.env" ]; then
    cp "$BASE_DIR/.env.template" "$BASE_DIR/.env"
    echo "Created .env file - PLEASE EDIT IT WITH YOUR CREDENTIALS"
fi

# Set permissions
echo "Setting permissions..."
chown -R www-data:www-data "$BASE_DIR/public"
chmod -R 755 "$BASE_DIR"
chmod 600 "$BASE_DIR/.env"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Edit $BASE_DIR/.env with your Notion credentials"
echo "2. Copy sync/, renderer/, and other code directories to $BASE_DIR/"
echo "3. Configure Nginx (see nginx.conf.example)"
echo "4. Run: sudo $BASE_DIR/install_scheduler.sh"
echo "5. Test manually: sudo -u www-data $BASE_DIR/venv/bin/python $BASE_DIR/sync/main.py"
echo ""
