#!/bin/bash
# INTRA-HUB v1.0 - Installation Check Script
# Verifies installation and configuration

echo "=== INTRA-HUB v1.0 Installation Check ==="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_ok() {
    echo -e "${GREEN}✓${NC} $1"
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    check_warn "Running as root (for check only, not required)"
else
    echo "Running as user: $(whoami)"
fi

echo ""
echo "--- Directory Structure ---"

if [ -d "/opt/intra-hub-v1.0" ]; then
    check_ok "/opt/intra-hub-v1.0 exists"
    
    for dir in sync renderer data public logs backups; do
        if [ -d "/opt/intra-hub-v1.0/$dir" ]; then
            check_ok "/opt/intra-hub-v1.0/$dir exists"
        else
            check_fail "/opt/intra-hub-v1.0/$dir missing"
        fi
    done
else
    check_fail "/opt/intra-hub-v1.0 does not exist"
fi

echo ""
echo "--- Python Environment ---"

if [ -d "/opt/intra-hub-v1.0/venv" ]; then
    check_ok "Virtual environment exists"
    
    if [ -f "/opt/intra-hub-v1.0/venv/bin/python" ]; then
        PYTHON_VERSION=$(/opt/intra-hub-v1.0/venv/bin/python --version 2>&1)
        check_ok "Python: $PYTHON_VERSION"
    fi
    
    # Check key packages
    for pkg in notion-client barcode dotenv; do
        if /opt/intra-hub-v1.0/venv/bin/python -c "import ${pkg//-/_}" 2>/dev/null; then
            check_ok "Package installed: $pkg"
        else
            check_fail "Package missing: $pkg"
        fi
    done
else
    check_fail "Virtual environment not found"
fi

echo ""
echo "--- Configuration ---"

if [ -f "/opt/intra-hub-v1.0/.env" ]; then
    check_ok ".env file exists"
    
    # Check if credentials are set (without revealing them)
    if grep -q "NOTION_TOKEN=secret_" /opt/intra-hub-v1.0/.env || \
       grep -q "NOTION_TOKEN=your_" /opt/intra-hub-v1.0/.env; then
        check_warn "NOTION_TOKEN appears to be template value"
    else
        check_ok "NOTION_TOKEN is set"
    fi
    
    if grep -q "NOTION_DATABASE_ID=2fa95c292b0e80b0a5b0f6a3d20b64f1" /opt/intra-hub-v1.0/.env; then
        check_ok "NOTION_DATABASE_ID is set"
    else
        check_warn "NOTION_DATABASE_ID may need verification"
    fi
else
    check_fail ".env file not found"
fi

echo ""
echo "--- Systemd Timer ---"

if systemctl list-unit-files | grep -q "intra-hub-sync.timer"; then
    check_ok "Timer unit installed"
    
    if systemctl is-enabled intra-hub-sync.timer >/dev/null 2>&1; then
        check_ok "Timer is enabled"
    else
        check_warn "Timer is not enabled"
    fi
    
    if systemctl is-active intra-hub-sync.timer >/dev/null 2>&1; then
        check_ok "Timer is active"
        
        # Show next execution
        NEXT_RUN=$(systemctl list-timers intra-hub-sync.timer --no-pager | grep intra-hub-sync.timer | awk '{print $1, $2}')
        echo "  Next run: $NEXT_RUN"
    else
        check_warn "Timer is not active"
    fi
else
    check_fail "Timer unit not installed"
fi

echo ""
echo "--- Nginx ---"

if command -v nginx >/dev/null 2>&1; then
    check_ok "Nginx is installed"
    
    if [ -f "/etc/nginx/sites-available/intra-hub" ]; then
        check_ok "Nginx config exists"
        
        if [ -L "/etc/nginx/sites-enabled/intra-hub" ]; then
            check_ok "Nginx config is enabled"
        else
            check_warn "Nginx config not enabled (symlink missing)"
        fi
    else
        check_warn "Nginx config not found"
    fi
    
    if systemctl is-active nginx >/dev/null 2>&1; then
        check_ok "Nginx is running"
    else
        check_fail "Nginx is not running"
    fi
else
    check_fail "Nginx is not installed"
fi

echo ""
echo "--- File Permissions ---"

if [ -d "/opt/intra-hub-v1.0/public" ]; then
    PUBLIC_OWNER=$(stat -c '%U:%G' /opt/intra-hub-v1.0/public 2>/dev/null || stat -f '%Su:%Sg' /opt/intra-hub-v1.0/public 2>/dev/null)
    if [ "$PUBLIC_OWNER" = "www-data:www-data" ]; then
        check_ok "public/ owned by www-data"
    else
        check_warn "public/ owner: $PUBLIC_OWNER (expected www-data:www-data)"
    fi
fi

if [ -f "/opt/intra-hub-v1.0/.env" ]; then
    ENV_PERMS=$(stat -c '%a' /opt/intra-hub-v1.0/.env 2>/dev/null || stat -f '%A' /opt/intra-hub-v1.0/.env 2>/dev/null)
    if [ "$ENV_PERMS" = "600" ]; then
        check_ok ".env permissions: 600"
    else
        check_warn ".env permissions: $ENV_PERMS (should be 600)"
    fi
fi

echo ""
echo "--- Test Sync (Dry Run) ---"

if [ -f "/opt/intra-hub-v1.0/.env" ] && [ -x "/opt/intra-hub-v1.0/venv/bin/python" ]; then
    echo "Testing Notion connection..."
    
    # Create minimal test script
    cat > /tmp/test_notion.py << 'EOFPYTHON'
import os
import sys
from dotenv import load_dotenv

load_dotenv('/opt/intra-hub-v1.0/.env')
token = os.getenv('NOTION_TOKEN')
db_id = os.getenv('NOTION_DATABASE_ID')

if not token or not db_id:
    print("ERROR: Credentials not set")
    sys.exit(1)

try:
    from notion_client import Client
    client = Client(auth=token)
    # Try to query database
    response = client.databases.query(database_id=db_id, page_size=1)
    print(f"SUCCESS: Connected to Notion database")
    print(f"Database has {len(response.get('results', []))} pages (showing first)")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
EOFPYTHON
    
    if /opt/intra-hub-v1.0/venv/bin/python /tmp/test_notion.py; then
        check_ok "Notion connection test passed"
    else
        check_fail "Notion connection test failed"
    fi
    
    rm -f /tmp/test_notion.py
else
    check_warn "Cannot run connection test (missing dependencies)"
fi

echo ""
echo "=== Check Complete ==="
echo ""
echo "Next steps:"
echo "  1. Fix any failed (✗) items above"
echo "  2. Address warnings (⚠) if needed"
echo "  3. Run manual sync: sudo systemctl start intra-hub-sync.service"
echo "  4. Check logs: sudo journalctl -u intra-hub-sync.service -f"
echo ""
