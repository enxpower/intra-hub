🚀 INTRA-HUB v1.0

Engineering-Grade Notion → Static Intranet Publisher

Overview

INTRA-HUB is a production-ready internal documentation publishing system.

It synchronizes content from a Notion database and generates a static intranet site with:

Structured document rendering

Code block preservation

Quote / Callout newline integrity

Search index generation

Automatic scheduled publishing

Designed for:

Engineering teams

Infrastructure documentation

Internal knowledge systems

Audit-friendly environments

System Architecture
Notion Database
        ↓
sync/main.py
        ↓
Block Renderer
        ↓
HTML Renderer
        ↓
/public static site
        ↓
nginx (internal access)

Deployment (5 Steps)
1️⃣ Clone Repository
git clone https://github.com/enxpower/intra-hub.git
cd intra-hub

2️⃣ Create Python Environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

3️⃣ Configure Environment
cp .env.template .env
nano .env


Set:

NOTION_API_KEY=your_key
NOTION_DATABASE_ID=your_db
PUBLISH_FIELD=publish

4️⃣ Run Initial Sync
python sync/main.py


You should see:

Rendered X documents
Generated search index
SUCCESS

5️⃣ Enable Automatic Publishing (Systemd)
sudo cp install_scheduler.sh /usr/local/bin/
sudo bash install_scheduler.sh


Default schedule:

02:00 UTC daily


Verify:

systemctl status intra-hub-sync.timer

Publish Logic

In Notion database:

Field	Type	Effect
publish	Checkbox	If checked → visible on intranet
unchecked	Hidden	Not rendered

Publishing occurs automatically at scheduled time.

File Structure
renderer/
sync/
public/
tools/
requirements.txt
setup.sh
install_scheduler.sh


Runtime folders (ignored by git):

venv/
data/
logs/
backups/
.env

Backup & Recovery

Full backup example:

tar czf intra-hub_fullbackup.tgz /opt/intra-hub-v1.0


Restore:

tar xzf intra-hub_fullbackup.tgz -C /opt


Restart service:

sudo systemctl start intra-hub-sync.timer

Rendering Guarantees

Code blocks preserve raw newlines

Quote blocks preserve line breaks

Callout blocks preserve formatting

No <br> pollution in <pre>

No content truncation on newline

Production Notes

Designed for internal network use

Nginx reverse proxy recommended

Systemd timer handles scheduling

Static output ensures reliability

No runtime DB required

Version

INTRA-HUB v1.0
Stable Production Baseline
Perfect Intranet System

