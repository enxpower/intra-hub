from .config import DELIMITERS as delimiters
#!/usr/bin/env python3
"""
INTRA-HUB v1.0 - HTML Renderer Main Module
Orchestrates document rendering, homepage, and search index generation
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

from renderer.barcode_generator import BarcodeGenerator
from renderer.block_renderer import NotionBlockRenderer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetricsManager:
    """Manages document metrics (views, downloads, shares)"""

    def __init__(self):
        self.metrics_file = Path("/opt/intra-hub/data/metrics/metrics.json")
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        self.metrics = self._load_metrics()

    def _load_metrics(self) -> Dict[str, Dict[str, int]]:
        """Load metrics from file"""
        if self.metrics_file.exists():
            with open(self.metrics_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_metrics(self):
        """Save metrics to file"""
        with open(self.metrics_file, "w", encoding="utf-8") as f:
            json.dump(self.metrics, f, indent=2, ensure_ascii=False)

    def get_metrics(self, doc_id: str) -> Dict[str, int]:
        """Get metrics for a document"""
        if doc_id not in self.metrics:
            self.metrics[doc_id] = {"views": 0, "downloads": 0, "shares": 0}
            self._save_metrics()
        return self.metrics[doc_id]

    def increment(self, doc_id: str, metric_type: str):
        """Increment a metric"""
        metrics = self.get_metrics(doc_id)
        metrics[metric_type] = metrics.get(metric_type, 0) + 1
        self._save_metrics()


class HTMLRenderer:
    """Main HTML rendering engine"""

    def __init__(self):
        self.cache_dir = Path("/opt/intra-hub/data/cache")
        self.public_dir = Path("/opt/intra-hub/public")
        self.docs_dir = self.public_dir / "documents"
        self.static_dir = self.public_dir / "static"

        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.static_dir.mkdir(parents=True, exist_ok=True)

        self.barcode_gen = BarcodeGenerator()
        self.block_renderer = NotionBlockRenderer()
        self.metrics = MetricsManager()

    def render_all_documents(self):
        """Render all published documents to HTML"""
        logger.info("Rendering all published documents...")

        published_file = self.cache_dir / "published_documents.json"
        if not published_file.exists():
            logger.warning("No published documents found")
            return

        with open(published_file, "r", encoding="utf-8") as f:
            published_docs = json.load(f)

        success_count = 0
        error_count = 0

        for doc_meta in published_docs:
            doc_id = doc_meta["doc_id"]
            try:
                self.render_document(doc_id)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to render {doc_id}: {e}")
                error_count += 1

        logger.info(f"Rendering complete: {success_count} success, {error_count} errors")

    def render_document(self, doc_id: str):
        """Render a single document to HTML"""
        cache_file = self.cache_dir / f"{doc_id}.json"
        if not cache_file.exists():
            raise FileNotFoundError(f"Cache file not found for {doc_id}")

        with open(cache_file, "r", encoding="utf-8") as f:
            content = json.load(f)

        title = content["title"]
        properties = content.get("properties", {})
        blocks = content.get("blocks", [])

        barcode_html = self.barcode_gen.get_barcode_html(doc_id)
        content_html = self._render_blocks_to_html(blocks)
        metrics = self.metrics.get_metrics(doc_id)
        property_html = self._build_property_table(properties)

        html = self._build_document_page(
            doc_id=doc_id,
            title=title,
            barcode_html=barcode_html,
            property_html=property_html,
            content_html=content_html,
            metrics=metrics,
        )

        output_file = self.docs_dir / f"{doc_id}.html"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"Rendered: {doc_id} -> {output_file}")

    def _render_blocks_to_html(self, blocks: List[Dict]) -> str:
        """Render list of blocks to HTML"""
        html_parts: List[str] = []

        current_list_type = None
        current_list_items: List[str] = []

        for block in blocks:
            block_type = block.get("type")

            if block_type in ["bulleted_list_item", "numbered_list_item"]:
                list_tag = "ul" if block_type == "bulleted_list_item" else "ol"

                if current_list_type != list_tag:
                    if current_list_type and current_list_items:
                        html_parts.append(
                            f"<{current_list_type}>{''.join(current_list_items)}</{current_list_type}>"
                        )
                        current_list_items = []
                    current_list_type = list_tag

                item_html = self.block_renderer.render_block(block)
                current_list_items.append(item_html)
            else:
                if current_list_type and current_list_items:
                    html_parts.append(
                        f"<{current_list_type}>{''.join(current_list_items)}</{current_list_type}>"
                    )
                    current_list_items = []
                    current_list_type = None

                html_parts.append(self.block_renderer.render_block(block))

        if current_list_type and current_list_items:
            html_parts.append(
                f"<{current_list_type}>{''.join(current_list_items)}</{current_list_type}>"
            )

        return "\n".join(html_parts)

    def _build_property_table(self, properties: Dict[str, Any]) -> str:
        """Build HTML table for document properties"""
        if not properties:
            return ""

        rows: List[str] = []
        for key, value in properties.items():
            if value is not None and value != "":
                rows.append(f"<tr><th>{key}</th><td>{value}</td></tr>")

        if not rows:
            return ""

        return (
            '<div class="document-properties">\n'
            "<h3>Document Properties</h3>\n"
            '<table class="properties-table">\n'
            f'{"".join(rows)}\n'
            "</table>\n"
            "</div>"
        )

    def _build_document_page(
        self,
        doc_id: str,
        title: str,
        barcode_html: str,
        property_html: str,
        content_html: str,
        metrics: Dict[str, int],
    ) -> str:
        """Build complete HTML document page (NO f-string; prevents KaTeX brace issues)"""

        css = self._get_document_css()

        html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>@@TITLE@@ - INTRA-HUB</title>
    <style>@@CSS@@</style>

    <!-- KaTeX for mathematical equations -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css" integrity="sha384-n8MVd4RsNIU0tAv4ct0nTaAbDJwPJzDEaqSD1odI+WdtXRGWt2kTvGFasHpSy3SV" crossorigin="anonymous">
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js" integrity="sha384-XjKyOOlGwcjNTAIQHIpgOno0Hl1YQqzUOEleOLALmuqehneUG+vnGctmUb0ZY0l8" crossorigin="anonymous"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js" integrity="sha384-+VBxd3r6XgURycqtZ117nYw44OOcIax56Z4dCRWbxyPt0Koah1uHoK0o4+/RRE05" crossorigin="anonymous"
        onload="renderMathInElement(document.body, {
            delimiters: [
                { left: '$$', right: '$$', display: true },
                { left: '$',  right: '$',  display: false }
            ]
        });"></script>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-left">
                <h1 class="doc-title">@@TITLE@@</h1>
                <div class="doc-id">Document ID: @@DOC_ID@@</div>
            </div>
            <div class="header-right">
                @@BARCODE_HTML@@
            </div>
        </div>

        <div class="metrics-bar">
            <span class="metric"><strong>Views:</strong> @@VIEWS@@</span>
            <span class="metric"><strong>Downloads:</strong> @@DOWNLOADS@@</span>
            <span class="metric"><strong>Shares:</strong> @@SHARES@@</span>
        </div>

        @@PROPERTY_HTML@@

        <div class="document-content">
            @@CONTENT_HTML@@
        </div>

        <div class="footer">
            <a href="/" class="back-link">&larr; Back to Homepage</a>
            <div class="timestamp">Last updated: @@TIMESTAMP@@</div>
        </div>
    </div>
</body>
</html>
"""

        html = (
            html_template.replace("@@TITLE@@", str(title))
            .replace("@@CSS@@", str(css))
            .replace("@@DOC_ID@@", str(doc_id))
            .replace("@@BARCODE_HTML@@", str(barcode_html))
            .replace("@@PROPERTY_HTML@@", str(property_html))
            .replace("@@CONTENT_HTML@@", str(content_html))
            .replace("@@VIEWS@@", str(metrics.get("views", 0)))
            .replace("@@DOWNLOADS@@", str(metrics.get("downloads", 0)))
            .replace("@@SHARES@@", str(metrics.get("shares", 0)))
            .replace("@@TIMESTAMP@@", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        return html

    def _get_document_css(self) -> str:
        """Return CSS for document pages"""
        return """
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    line-height: 1.6;
    color: #333;
    background: #f5f5f5;
    padding: 20px;
}

.container {
    max-width: 900px;
    margin: 0 auto;
    background: white;
    padding: 40px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    border-radius: 8px;
}

.header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 30px;
    padding-bottom: 10px;
}

.header-left {
    flex: 1;
}

.header-right {
    margin-left: 40px;
    text-align: right;
    flex-shrink: 0;
}

.doc-title {
    font-size: 2em;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 10px;
}

.doc-id {
    font-size: 0.9em;
    color: #666;
    font-family: "Courier New", monospace;
}

.barcode {
    max-width: 280px;
    width: 100%;
    height: auto;
    display: block;
}

.metrics-bar {
    display: flex;
    gap: 30px;
    padding: 15px 20px;
    background: #f8f9fa;
    border-radius: 6px;
    margin-bottom: 30px;
    font-size: 0.9em;
}

.metric {
    color: #555;
}

.document-properties {
    margin-bottom: 30px;
    padding: 20px;
    background: #fafafa;
    border-left: 4px solid #2196F3;
    border-radius: 4px;
}

.document-properties h3 {
    margin-bottom: 15px;
    color: #2196F3;
    font-size: 1.1em;
}

.properties-table {
    width: 100%;
    border-collapse: collapse;
}

.properties-table th {
    text-align: left;
    padding: 8px 12px;
    background: #e8e8e8;
    font-weight: 600;
    width: 150px;
}

.properties-table td {
    padding: 8px 12px;
    border-bottom: 1px solid #e0e0e0;
}

.document-content {
    line-height: 1.8;
}

.document-content p {
    margin-bottom: 1em;
}

.document-content h1, .document-content h2, .document-content h3 {
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    font-weight: 600;
}

.document-content h1 { font-size: 1.8em; }
.document-content h2 { font-size: 1.5em; }
.document-content h3 { font-size: 1.3em; }

.document-content ul, .document-content ol {
    margin-left: 2em;
    margin-bottom: 1em;
}

.document-content li {
    margin-bottom: 0.5em;
}

.document-content blockquote {
    border-left: 4px solid #ddd;
    padding-left: 20px;
    margin: 1.5em 0;
    color: #666;
    font-style: italic;
}

.document-content code {
    background: #f4f4f4;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: "Courier New", Courier, monospace;
    font-size: 0.9em;
}

/* Notion-style code blocks - light background */
.code-block {
    margin: 1.5em 0;
    border-radius: 6px;
    overflow: hidden;
    border: 1px solid #e0e0e0;
    background: #f7f7f7;
}

.code-header {
    background: #e8e8e8;
    color: #555;
    padding: 8px 15px;
    font-size: 0.85em;
    border-bottom: 1px solid #d0d0d0;
    font-weight: 500;
}

.code-block pre {
    background: #f7f7f7;
    color: #24292e;
    padding: 20px;
    overflow-x: auto;
    margin: 0;
    font-family: "SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, "Courier New", monospace;
    font-size: 0.9em;
    line-height: 1.5;
}

.code-block code {
    background: transparent;
    color: inherit;
    padding: 0;
}

.callout {
    display: flex;
    gap: 12px;
    padding: 15px;
    margin: 1.5em 0;
    background: #f0f7ff;
    border-radius: 6px;
    border-left: 4px solid #2196F3;
}

.callout-icon {
    font-size: 1.5em;
}

.table-wrapper {
    overflow-x: auto;
    margin: 1.5em 0;
}

.notion-table {
    width: 100%;
    border-collapse: collapse;
    border: 1px solid #ddd;
    font-size: 0.95em;
}

.notion-table th, .notion-table td {
    padding: 10px 12px;
    border: 1px solid #ddd;
    text-align: left;
}

.notion-table thead th {
    background: #f5f5f5;
    font-weight: 600;
    color: #333;
}

.notion-table tbody th {
    background: #fafafa;
    font-weight: 600;
}

.notion-table tbody tr:hover {
    background: #f9f9f9;
}

.table-placeholder {
    text-align: center;
    padding: 40px 20px !important;
    color: #999;
    font-style: italic;
}

.image-block {
    margin: 1.5em 0;
    text-align: center;
}

.image-block img {
    max-width: 100%;
    height: auto;
    border-radius: 4px;
}

.image-block figcaption {
    margin-top: 10px;
    font-size: 0.9em;
    color: #666;
}

.file-download {
    margin: 1em 0;
    padding: 15px;
    background: #f8f9fa;
    border-radius: 6px;
}

.download-link {
    color: #2196F3;
    text-decoration: none;
    font-weight: 500;
}

.download-link:hover {
    text-decoration: underline;
}

.todo-item {
    margin: 0.5em 0;
    display: flex;
    gap: 8px;
}

.todo-item.checked {
    color: #999;
    text-decoration: line-through;
}

.equation {
    margin: 1.5em 0;
    padding: 20px;
    background: #fafafa;
    border-radius: 4px;
    text-align: center;
    overflow-x: auto;
    font-size: 1.1em;
}

.unknown-block {
    padding: 10px;
    margin: 1em 0;
    background: #fff3cd;
    border-left: 4px solid #ffc107;
    border-radius: 4px;
    font-size: 0.9em;
}

.render-error {
    padding: 15px;
    background: #ffe6e6;
    border-left: 4px solid #f44336;
    border-radius: 4px;
    color: #c62828;
    margin: 1em 0;
}

.footer {
    margin-top: 50px;
    padding-top: 20px;
    border-top: 1px solid #e0e0e0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.back-link {
    color: #2196F3;
    text-decoration: none;
    font-weight: 500;
}

.back-link:hover {
    text-decoration: underline;
}

.timestamp {
    font-size: 0.85em;
    color: #999;
}

@media print {
    body {
        background: white;
        padding: 0;
    }

    .container {
        box-shadow: none;
        padding: 20px;
    }

    .metrics-bar, .footer {
        display: none;
    }
}
"""

    def generate_homepage(self):
        """Generate homepage with paginated document list"""
        logger.info("Generating homepage...")

        published_file = self.cache_dir / "published_documents.json"
        if not published_file.exists():
            logger.warning("No published documents for homepage")
            self._create_empty_homepage()
            return

        with open(published_file, "r", encoding="utf-8") as f:
            docs = json.load(f)

        docs.sort(key=lambda x: x["doc_id"], reverse=True)

        items_per_page = 10
        total_pages = (len(docs) + items_per_page - 1) // items_per_page

        for page_num in range(1, total_pages + 1):
            start_idx = (page_num - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_docs = docs[start_idx:end_idx]

            html = self._build_homepage_html(page_docs, page_num, total_pages)

            if page_num == 1:
                output_file = self.public_dir / "index.html"
            else:
                output_file = self.public_dir / f"page-{page_num}.html"

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html)

            logger.info(f"Generated homepage page {page_num}/{total_pages}")

    def _create_empty_homepage(self):
        """Create empty homepage when no documents published"""
        html = self._build_homepage_html([], 1, 1)
        with open(self.public_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(html)

    def _build_homepage_html(self, docs: List[Dict], page_num: int, total_pages: int) -> str:
        """Build homepage HTML"""
        rows = []
        for doc in docs:
            metrics = self.metrics.get_metrics(doc["doc_id"])
            props = doc.get("properties", {})

            category = props.get("CATEGORY", "-")
            author = props.get("AUTHOR", "-")
            version = props.get("VERSION", "-")
            tags = props.get("TAGS", "-")

            row = f"""<tr>
    <td class="doc-id"><a href="/documents/{doc['doc_id']}.html">{doc['doc_id']}</a></td>
    <td class="doc-title"><a href="/documents/{doc['doc_id']}.html">{doc['title']}</a></td>
    <td>{category}</td>
    <td>{author}</td>
    <td>{version}</td>
    <td>{tags}</td>
    <td>{metrics['views']}</td>
    <td>{metrics['downloads']}</td>
    <td>{metrics['shares']}</td>
</tr>"""
            rows.append(row)

        table_html = "\n".join(rows) if rows else '<tr><td colspan="9" class="empty-state">No documents published</td></tr>'
        pagination_html = self._build_pagination(page_num, total_pages)
        css = self._get_homepage_css()

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>INTRA-HUB - Internal Documentation</title>
    <style>{css}</style>
</head>
<body>
    <div class="header">
        <h1>INTRA-HUB</h1>
        <p class="subtitle">Internal Documentation Portal</p>
    </div>

    <div class="container">
        <div class="stats">
            <div class="stat-item">
                <div class="stat-number">{len(docs)}</div>
                <div class="stat-label">Documents on this page</div>
            </div>
        </div>

        <div class="table-container">
            <table class="doc-table">
                <thead>
                    <tr>
                        <th>Document ID</th>
                        <th>Title</th>
                        <th>Category</th>
                        <th>Author</th>
                        <th>Version</th>
                        <th>Tags</th>
                        <th>Views</th>
                        <th>Downloads</th>
                        <th>Shares</th>
                    </tr>
                </thead>
                <tbody>
                    {table_html}
                </tbody>
            </table>
        </div>

        {pagination_html}

        <div class="footer">
            <p>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p class="notice">Internal Use Only - VPN Access Required</p>
        </div>
    </div>
</body>
</html>"""

    def _build_pagination(self, current_page: int, total_pages: int) -> str:
        """Build pagination links"""
        if total_pages <= 1:
            return ""

        links: List[str] = []

        if current_page > 1:
            prev_url = "index.html" if current_page == 2 else f"page-{current_page - 1}.html"
            links.append(f'<a href="/{prev_url}" class="page-link">&larr; Previous</a>')

        for i in range(1, total_pages + 1):
            url = "index.html" if i == 1 else f"page-{i}.html"
            if i == current_page:
                links.append(f'<span class="page-link active">{i}</span>')
            else:
                links.append(f'<a href="/{url}" class="page-link">{i}</a>')

        if current_page < total_pages:
            next_url = f"page-{current_page + 1}.html"
            links.append(f'<a href="/{next_url}" class="page-link">Next &rarr;</a>')

        return f'<div class="pagination">{" ".join(links)}</div>'

    def _get_homepage_css(self) -> str:
        """Return CSS for homepage"""
        return """
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    padding: 20px;
}

.header {
    text-align: center;
    color: white;
    padding: 40px 20px;
}

.header h1 {
    font-size: 3em;
    font-weight: 700;
    margin-bottom: 10px;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
}

.subtitle {
    font-size: 1.2em;
    opacity: 0.9;
}

.container {
    max-width: 1400px;
    margin: 0 auto;
    background: white;
    border-radius: 12px;
    padding: 40px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
}

.stats {
    display: flex;
    gap: 20px;
    margin-bottom: 30px;
    padding-bottom: 20px;
    border-bottom: 2px solid #e0e0e0;
}

.stat-item {
    text-align: center;
}

.stat-number {
    font-size: 2.5em;
    font-weight: 700;
    color: #667eea;
}

.stat-label {
    font-size: 0.9em;
    color: #666;
    margin-top: 5px;
}

.table-container {
    overflow-x: auto;
    margin-bottom: 30px;
}

.doc-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.95em;
}

.doc-table thead {
    background: #f8f9fa;
}

.doc-table th {
    padding: 15px 12px;
    text-align: left;
    font-weight: 600;
    color: #333;
    border-bottom: 2px solid #dee2e6;
    white-space: nowrap;
}

.doc-table td {
    padding: 15px 12px;
    border-bottom: 1px solid #e9ecef;
}

.doc-table tbody tr:hover {
    background: #f8f9fa;
}

.doc-id {
    font-family: "Courier New", monospace;
    font-weight: 600;
}

.doc-id a, .doc-title a {
    color: #667eea;
    text-decoration: none;
}

.doc-id a:hover, .doc-title a:hover {
    text-decoration: underline;
}

.doc-title {
    font-weight: 500;
}

.empty-state {
    text-align: center;
    padding: 60px 20px !important;
    color: #999;
    font-style: italic;
}

.pagination {
    display: flex;
    justify-content: center;
    gap: 10px;
    margin: 30px 0;
}

.page-link {
    padding: 8px 16px;
    border: 1px solid #ddd;
    border-radius: 4px;
    text-decoration: none;
    color: #667eea;
    background: white;
    transition: all 0.2s;
}

.page-link:hover {
    background: #667eea;
    color: white;
    border-color: #667eea;
}

.page-link.active {
    background: #667eea;
    color: white;
    border-color: #667eea;
    font-weight: 600;
}

.footer {
    margin-top: 40px;
    padding-top: 20px;
    border-top: 1px solid #e0e0e0;
    text-align: center;
    color: #666;
    font-size: 0.9em;
}

.notice {
    margin-top: 10px;
    color: #999;
    font-style: italic;
}
"""

    def generate_search_index(self):
        """Generate search index JSON for client-side search"""
        logger.info("Generating search index...")

        published_file = self.cache_dir / "published_documents.json"
        if not published_file.exists():
            return

        with open(published_file, "r", encoding="utf-8") as f:
            docs = json.load(f)

        search_index = []
        for doc in docs:
            search_index.append(
                {
                    "doc_id": doc["doc_id"],
                    "title": doc["title"],
                    "category": doc.get("properties", {}).get("CATEGORY", ""),
                    "author": doc.get("properties", {}).get("AUTHOR", ""),
                    "tags": doc.get("properties", {}).get("TAGS", ""),
                    "url": f'/documents/{doc["doc_id"]}.html',
                }
            )

        with open(self.public_dir / "search-index.json", "w", encoding="utf-8") as f:
            json.dump(search_index, f, ensure_ascii=False, indent=2)

        logger.info(f"Search index generated with {len(search_index)} documents")

    def cleanup_revoked_documents(self):
        """Remove HTML files for documents no longer published"""
        logger.info("Cleaning up revoked documents...")

        published_file = self.cache_dir / "published_documents.json"
        if published_file.exists():
            with open(published_file, "r", encoding="utf-8") as f:
                published_docs = json.load(f)
            published_ids = {doc["doc_id"] for doc in published_docs}
        else:
            published_ids = set()

        removed_count = 0
        for html_file in self.docs_dir.glob("DOC-*.html"):
            doc_id = html_file.stem
            if doc_id not in published_ids:
                html_file.unlink()
                logger.info(f"Removed revoked document: {doc_id}")
                removed_count += 1

        logger.info(f"Cleanup complete: {removed_count} files removed")


if __name__ == "__main__":
    renderer = HTMLRenderer()
    renderer.render_all_documents()
    renderer.generate_homepage()
    renderer.generate_search_index()
    renderer.cleanup_revoked_documents()
