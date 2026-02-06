#!/usr/bin/env python3
"""
INTRA-HUB v1.0 - Main Sync Entry Point
Orchestrates the complete sync and render pipeline
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sync.notion_sync import NotionSync
from renderer.html_renderer import HTMLRenderer
from renderer.barcode_generator import BarcodeGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/intra-hub/logs/main.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def create_backup():
    """Create full system backup before sync"""
    logger.info("Creating pre-sync backup...")
    
    import subprocess
    from datetime import datetime
    
    backup_dir = Path('/opt/intra-hub/backups')
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    backup_file = backup_dir / f"intra-hub_fullbackup_{timestamp}.tgz"
    
    try:
        # Backup critical directories
        subprocess.run([
            'tar', 'czf', str(backup_file),
            '-C', '/opt/intra-hub',
            'public', 'data', 'renderer', 'sync',
            '--exclude=*.pyc',
            '--exclude=__pycache__'
        ], check=True)
        
        logger.info(f"Backup created: {backup_file}")
        
        # Keep only last 7 backups
        backups = sorted(backup_dir.glob('intra-hub_fullbackup_*.tgz'))
        if len(backups) > 7:
            for old_backup in backups[:-7]:
                old_backup.unlink()
                logger.info(f"Removed old backup: {old_backup}")
                
    except Exception as e:
        logger.warning(f"Backup failed (non-critical): {e}")


def main():
    """Main pipeline execution"""
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("INTRA-HUB v1.0 - Daily Sync Pipeline Started")
    logger.info(f"Start Time: {start_time}")
    logger.info("=" * 60)
    
    # Create backup
    try:
        create_backup()
    except Exception as e:
        logger.warning(f"Backup failed: {e}")
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv('/opt/intra-hub/.env')
    
    token = os.getenv('NOTION_TOKEN')
    database_id = os.getenv('NOTION_DATABASE_ID')
    
    if not token or not database_id:
        logger.error("NOTION_TOKEN and NOTION_DATABASE_ID must be set")
        sys.exit(1)
    
    try:
        # Step 1: Sync from Notion
        logger.info("Step 1: Syncing from Notion...")
        syncer = NotionSync(token, database_id)
        pages = syncer.fetch_all_pages()
        result = syncer.process_pages(pages)
        syncer.fetch_and_cache_content(result['published_only'])
        
        # Step 2: Render HTML
        logger.info("Step 2: Rendering HTML pages...")
        renderer = HTMLRenderer()
        renderer.render_all_documents()
        renderer.generate_homepage()
        
        # Step 3: Generate search index
        logger.info("Step 3: Generating search index...")
        renderer.generate_search_index()
        
        # Step 4: Cleanup revoked documents
        logger.info("Step 4: Cleaning up revoked documents...")
        renderer.cleanup_revoked_documents()
        
        # Done
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info("Pipeline Completed Successfully")
        logger.info(f"Total Documents: {result['total_documents']}")
        logger.info(f"Published Documents: {result['published_documents']}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"End Time: {end_time}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
