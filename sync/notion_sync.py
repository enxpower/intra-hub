#!/usr/bin/env python3
"""
INTRA-HUB v1.0 - Notion Sync Module
Pulls data from Notion database and manages document lifecycle
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from notion_client import Client

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/intra-hub/logs/sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class NotionSync:
    """Handles synchronization with Notion database"""
    
    def __init__(self, token: str, database_id: str):
        self.client = Client(auth=token)
        self.database_id = database_id
        self.data_dir = Path('/opt/intra-hub/data')
        self.cache_dir = self.data_dir / 'cache'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Document number counter file
        self.counter_file = self.data_dir / 'doc_counter.json'
        self.doc_mapping_file = self.data_dir / 'doc_mapping.json'
        
    def load_counter(self) -> int:
        """Load current document counter"""
        if self.counter_file.exists():
            with open(self.counter_file, 'r') as f:
                data = json.load(f)
                return data.get('counter', 0)
        return 0
    
    def save_counter(self, counter: int):
        """Save document counter"""
        with open(self.counter_file, 'w') as f:
            json.dump({'counter': counter, 'updated_at': datetime.now().isoformat()}, f)
    
    def load_doc_mapping(self) -> Dict[str, str]:
        """Load Notion page ID to DOC_ID mapping"""
        if self.doc_mapping_file.exists():
            with open(self.doc_mapping_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_doc_mapping(self, mapping: Dict[str, str]):
        """Save Notion page ID to DOC_ID mapping"""
        with open(self.doc_mapping_file, 'w') as f:
            json.dump(mapping, f, indent=2)
    
    def generate_doc_id(self, counter: int) -> str:
        """Generate document ID in format DOC-NNNN"""
        return f"DOC-{counter:04d}"
    
    def extract_property_value(self, prop: Dict[str, Any]) -> Optional[str]:
        """Extract value from Notion property based on type"""
        prop_type = prop.get('type')
        
        if prop_type == 'title':
            if prop.get('title'):
                return ''.join([t.get('plain_text', '') for t in prop['title']])
        elif prop_type == 'rich_text':
            if prop.get('rich_text'):
                return ''.join([t.get('plain_text', '') for t in prop['rich_text']])
        elif prop_type == 'select':
            if prop.get('select'):
                return prop['select'].get('name')
        elif prop_type == 'multi_select':
            if prop.get('multi_select'):
                return ', '.join([t.get('name', '') for t in prop['multi_select']])
        elif prop_type == 'checkbox':
            return prop.get('checkbox', False)
        elif prop_type == 'number':
            return prop.get('number')
        elif prop_type == 'date':
            if prop.get('date'):
                return prop['date'].get('start')
        elif prop_type == 'people':
            if prop.get('people'):
                return ', '.join([p.get('name', '') for p in prop['people']])
        elif prop_type == 'email':
            return prop.get('email')
        elif prop_type == 'phone_number':
            return prop.get('phone_number')
        elif prop_type == 'url':
            return prop.get('url')
        
        return None
    
    def fetch_all_pages(self) -> List[Dict]:
        """Fetch all pages from Notion database"""
        logger.info(f"Fetching pages from database {self.database_id}")
        
        all_pages = []
        has_more = True
        start_cursor = None
        
        while has_more:
            try:
                response = self.client.databases.query(
                    database_id=self.database_id,
                    start_cursor=start_cursor
                )
                all_pages.extend(response.get('results', []))
                has_more = response.get('has_more', False)
                start_cursor = response.get('next_cursor')
            except Exception as e:
                logger.error(f"Error fetching pages: {e}")
                raise
        
        logger.info(f"Fetched {len(all_pages)} pages from Notion")
        return all_pages
    
    def update_notion_doc_id(self, page_id: str, doc_id: str):
        """Write DOC_ID back to Notion"""
        try:
            self.client.pages.update(
                page_id=page_id,
                properties={
                    'DOC_ID': {
                        'rich_text': [
                            {
                                'text': {
                                    'content': doc_id
                                }
                            }
                        ]
                    }
                }
            )
            logger.info(f"Updated Notion page {page_id} with DOC_ID: {doc_id}")
        except Exception as e:
            logger.error(f"Failed to update DOC_ID for page {page_id}: {e}")
    
    def process_pages(self, pages: List[Dict]) -> Dict[str, Any]:
        """Process pages and assign document numbers"""
        counter = self.load_counter()
        doc_mapping = self.load_doc_mapping()
        
        processed_docs = []
        published_docs = []
        
        for page in pages:
            try:
                page_id = page['id']
                props = page.get('properties', {})
                
                # Extract core fields
                title = self.extract_property_value(props.get('TITLE', {})) or 'Untitled'
                publish = self.extract_property_value(props.get('PUBLISH', {})) or False
                
                # Check if DOC_ID already exists in Notion
                existing_doc_id = self.extract_property_value(props.get('DOC_ID', {}))
                
                # Assign DOC_ID if not present
                if page_id not in doc_mapping and not existing_doc_id:
                    # First publication - assign new DOC_ID
                    counter += 1
                    doc_id = self.generate_doc_id(counter)
                    doc_mapping[page_id] = doc_id
                    
                    # Write back to Notion
                    self.update_notion_doc_id(page_id, doc_id)
                elif existing_doc_id and page_id not in doc_mapping:
                    # Notion has DOC_ID but local mapping doesn't - sync from Notion
                    doc_mapping[page_id] = existing_doc_id
                    # Extract counter from DOC_ID
                    try:
                        doc_num = int(existing_doc_id.split('-')[1])
                        counter = max(counter, doc_num)
                    except:
                        pass
                elif page_id in doc_mapping and not existing_doc_id:
                    # Local has DOC_ID but Notion doesn't - write to Notion
                    self.update_notion_doc_id(page_id, doc_mapping[page_id])
                
                doc_id = doc_mapping.get(page_id, 'UNASSIGNED')
                
                # Extract all available properties
                doc_data = {
                    'page_id': page_id,
                    'doc_id': doc_id,
                    'title': title,
                    'publish': publish,
                    'created_time': page.get('created_time'),
                    'last_edited_time': page.get('last_edited_time'),
                    'url': page.get('url'),
                    'properties': {}
                }
                
                # Extract all properties for homepage display
                for prop_name, prop_value in props.items():
                    if prop_name not in ['TITLE', 'PUBLISH', 'DOC_ID']:
                        value = self.extract_property_value(prop_value)
                        if value is not None:
                            doc_data['properties'][prop_name] = value
                
                processed_docs.append(doc_data)
                
                if publish:
                    published_docs.append(doc_data)
                    
            except Exception as e:
                logger.error(f"Error processing page {page.get('id')}: {e}")
                continue
        
        # Save updated counter and mapping
        self.save_counter(counter)
        self.save_doc_mapping(doc_mapping)
        
        # Save processed data
        output = {
            'sync_time': datetime.now().isoformat(),
            'total_documents': len(processed_docs),
            'published_documents': len(published_docs),
            'all_documents': processed_docs,
            'published_only': published_docs
        }
        
        with open(self.cache_dir / 'all_documents.json', 'w') as f:
            json.dump(processed_docs, f, indent=2, ensure_ascii=False)
        
        with open(self.cache_dir / 'published_documents.json', 'w') as f:
            json.dump(published_docs, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Processed {len(processed_docs)} documents, {len(published_docs)} published")
        
        return output
    
    def fetch_page_blocks(self, page_id: str) -> List[Dict]:
        """Fetch all blocks (content) from a Notion page, including children"""
        blocks = []
        has_more = True
        start_cursor = None
        
        while has_more:
            try:
                response = self.client.blocks.children.list(
                    block_id=page_id,
                    start_cursor=start_cursor
                )
                fetched_blocks = response.get('results', [])
                
                # Recursively fetch children for blocks that have them
                for block in fetched_blocks:
                    if block.get('has_children', False):
                        # Fetch child blocks recursively
                        child_blocks = self.fetch_page_blocks(block['id'])
                        block['children'] = child_blocks
                    
                blocks.extend(fetched_blocks)
                has_more = response.get('has_more', False)
                start_cursor = response.get('next_cursor')
            except Exception as e:
                logger.error(f"Error fetching blocks for page {page_id}: {e}")
                break
        
        return blocks
    
    def fetch_and_cache_content(self, published_docs: List[Dict]):
        """Fetch full content for all published documents"""
        logger.info(f"Fetching content for {len(published_docs)} published documents")
        
        for doc in published_docs:
            page_id = doc['page_id']
            doc_id = doc['doc_id']
            
            try:
                blocks = self.fetch_page_blocks(page_id)
                
                content_data = {
                    'doc_id': doc_id,
                    'page_id': page_id,
                    'title': doc['title'],
                    'properties': doc.get('properties', {}),
                    'blocks': blocks,
                    'fetched_at': datetime.now().isoformat()
                }
                
                # Save to cache
                cache_file = self.cache_dir / f"{doc_id}.json"
                with open(cache_file, 'w') as f:
                    json.dump(content_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Cached content for {doc_id}: {len(blocks)} blocks")
                
            except Exception as e:
                logger.error(f"Error fetching content for {doc_id}: {e}")
                continue


def main():
    """Main sync execution"""
    logger.info("=== INTRA-HUB Sync Started ===")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv('/opt/intra-hub/.env')
    
    token = os.getenv('NOTION_TOKEN')
    database_id = os.getenv('NOTION_DATABASE_ID')
    
    if not token or not database_id:
        logger.error("NOTION_TOKEN and NOTION_DATABASE_ID must be set in .env")
        sys.exit(1)
    
    try:
        syncer = NotionSync(token, database_id)
        
        # Step 1: Fetch all pages
        pages = syncer.fetch_all_pages()
        
        # Step 2: Process and assign DOC_IDs
        result = syncer.process_pages(pages)
        
        # Step 3: Fetch full content for published docs
        published_docs = result['published_only']
        syncer.fetch_and_cache_content(published_docs)
        
        logger.info("=== Sync Completed Successfully ===")
        logger.info(f"Total: {result['total_documents']}, Published: {result['published_documents']}")
        
    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
