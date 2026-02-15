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
        self.metrics_file = Path("/opt/intra-hub-v1.0/data/metrics/metrics.json")
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
        self.cache_dir = Path("/opt/intra-hub-v1.0/data/cache")
        self.public_dir = Path("/opt/intra-hub-v1.0/public")
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
        """Return CSS for document pages - Enhanced mobile-responsive design"""
        return """
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
    line-height: 1.7;
    color: #2c3e50;
    background: #f5f7fa;
    padding: 20px;
}

.container {
    max-width: 900px;
    margin: 0 auto;
    background: white;
    padding: 45px 50px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    border-radius: 10px;
}

/* 文档头部 */
.header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 35px;
    padding-bottom: 10px;
}

.header-left {
    flex: 1;
}

.header-right {
    margin-left: 30px;
    text-align: right;
    flex-shrink: 0;
}

.doc-title {
    font-size: 2em;
    font-weight: 600;
    color: #1a1a1a;
    margin-bottom: 12px;
    line-height: 1.3;
    letter-spacing: -0.3px;
}

.doc-id {
    font-size: 0.9em;
    color: #7f8c8d;
    font-family: "SF Mono", Monaco, Consolas, "Courier New", monospace;
    font-weight: 500;
}

/* 条形码 - 精细化 */
.barcode {
    max-width: 280px;
    width: 100%;
    height: auto;
    display: block;
}

/* 指标栏 */
.metrics-bar {
    display: flex;
    gap: 25px;
    padding: 16px 20px;
    background: #f8f9fa;
    border-radius: 8px;
    margin-bottom: 30px;
    font-size: 0.88em;
    border: 1px solid #e8e8e8;
    flex-wrap: wrap;
}

.metric {
    color: #7f8c8d;
}

.metric strong {
    color: #2c3e50;
    font-weight: 600;
}

/* 文档属性 */
.document-properties {
    margin-bottom: 35px;
    padding: 22px;
    background: #f8f9fa;
    border-left: 4px solid #3498db;
    border-radius: 6px;
}

.document-properties h3 {
    margin-bottom: 16px;
    color: #3498db;
    font-size: 1em;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.properties-table {
    width: 100%;
    border-collapse: collapse;
}

.properties-table th {
    text-align: left;
    padding: 10px 14px;
    background: #e8e8e8;
    font-weight: 600;
    width: 140px;
    font-size: 0.88em;
    color: #2c3e50;
}

.properties-table td {
    padding: 10px 14px;
    border-bottom: 1px solid #e8e8e8;
    color: #34495e;
}

.properties-table tr:last-child td {
    border-bottom: none;
}

/* 文档内容 */
.document-content {
    line-height: 1.8;
    font-size: 16px;
    color: #34495e;
}

.document-content p {
    margin-bottom: 1.2em;
}

.document-content h1,
.document-content h2,
.document-content h3 {
    margin-top: 1.8em;
    margin-bottom: 0.6em;
    font-weight: 600;
    color: #2c3e50;
    line-height: 1.3;
}

.document-content h1 { 
    font-size: 1.8em;
    border-bottom: 2px solid #e8e8e8;
    padding-bottom: 0.3em;
}

.document-content h2 { 
    font-size: 1.5em;
}

.document-content h3 { 
    font-size: 1.25em;
    color: #34495e;
}

.document-content ul,
.document-content ol {
    margin-left: 1.8em;
    margin-bottom: 1.2em;
}

.document-content li {
    margin-bottom: 0.5em;
}

.document-content blockquote {
    border-left: 4px solid #e0e0e0;
    padding-left: 20px;
    margin: 1.5em 0;
    color: #7f8c8d;
    font-style: italic;
}

.document-content code {
    background: #f5f5f5;
    padding: 3px 6px;
    border-radius: 3px;
    font-family: "SF Mono", Monaco, Consolas, "Courier New", monospace;
    font-size: 0.88em;
    color: #e74c3c;
}

/* 代码块 - 去除语言标签，Notion 风格 */
.code-block {
    margin: 1.8em 0;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #e0e0e0;
    background: #f7f7f7;
}

.code-block pre {
    background: #f7f7f7;
    color: #2c3e50;
    padding: 20px 24px;
    overflow-x: auto;
    margin: 0;
    font-family: "SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, "Courier New", monospace;
    font-size: 0.88em;
    line-height: 1.6;
}

.code-block code {
    background: transparent;
    color: inherit;
    padding: 0;
    border-radius: 0;
}

/* Callout */
.callout {
    display: flex;
    gap: 14px;
    padding: 18px;
    margin: 1.5em 0;
    background: #e8f4fd;
    border-radius: 8px;
    border-left: 4px solid #3498db;
}

.callout-icon {
    font-size: 1.4em;
    flex-shrink: 0;
}

.callout-content {
    flex: 1;
}

/* 表格 */
.table-wrapper {
    overflow-x: auto;
    margin: 1.8em 0;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
}

.notion-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.92em;
}

.notion-table th,
.notion-table td {
    padding: 12px 14px;
    border: 1px solid #e8e8e8;
    text-align: left;
}

.notion-table thead th {
    background: #f8f9fa;
    font-weight: 600;
    color: #2c3e50;
}

.notion-table tbody th {
    background: #fafafa;
    font-weight: 600;
}

.notion-table tbody tr:hover {
    background: #f8f9fa;
}

.table-placeholder {
    text-align: center;
    padding: 50px 20px !important;
    color: #bdc3c7;
    font-style: italic;
}

/* 图片 */
.image-block {
    margin: 1.8em 0;
    text-align: center;
}

.image-block img {
    max-width: 100%;
    height: auto;
    border-radius: 6px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.image-block figcaption {
    margin-top: 12px;
    font-size: 0.88em;
    color: #7f8c8d;
    font-style: italic;
}

/* 文件下载 */
.file-download {
    margin: 1.2em 0;
    padding: 16px 18px;
    background: #f8f9fa;
    border-radius: 6px;
    border: 1px solid #e8e8e8;
}

.download-link {
    color: #3498db;
    text-decoration: none;
    font-weight: 500;
    transition: color 0.2s ease;
}

.download-link:hover {
    color: #2980b9;
    text-decoration: underline;
}

/* TODO 项 */
.todo-item {
    margin: 0.6em 0;
    display: flex;
    gap: 10px;
    align-items: flex-start;
}

.todo-item.checked {
    color: #95a5a6;
    text-decoration: line-through;
}

.checkbox {
    flex-shrink: 0;
    font-size: 1.1em;
}

/* 数学公式 */
.equation {
    margin: 1.8em 0;
    padding: 25px;
    background: #f8f9fa;
    border-radius: 8px;
    text-align: center;
    overflow-x: auto;
    font-size: 1.05em;
    border: 1px solid #e8e8e8;
}

/* 未知块 */
.unknown-block {
    padding: 12px;
    margin: 1.2em 0;
    background: #fff3cd;
    border-left: 4px solid #ffc107;
    border-radius: 6px;
    font-size: 0.9em;
}

/* 渲染错误 */
.render-error {
    padding: 16px;
    background: #fee;
    border-left: 4px solid #e74c3c;
    border-radius: 6px;
    color: #c0392b;
    margin: 1.2em 0;
}

/* 页脚 */
.footer {
    margin-top: 50px;
    padding-top: 25px;
    border-top: 1px solid #e8e8e8;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 15px;
}

.back-link {
    color: #3498db;
    text-decoration: none;
    font-weight: 500;
    transition: color 0.2s ease;
}

.back-link:hover {
    color: #2980b9;
}

.timestamp {
    font-size: 0.85em;
    color: #95a5a6;
}

/* ========== 移动端适配 ========== */

@media (max-width: 768px) {
    body {
        padding: 10px;
    }
    
    .container {
        padding: 25px 20px;
        border-radius: 8px;
    }
    
    .header {
        flex-direction: column;
        gap: 20px;
    }
    
    .header-right {
        margin-left: 0;
        text-align: center;
        width: 100%;
    }
    
    .barcode {
        margin: 0 auto;
        max-width: 240px;
    }
    
    .doc-title {
        font-size: 1.6em;
    }
    
    .metrics-bar {
        gap: 15px;
        padding: 14px 16px;
        font-size: 0.85em;
    }
    
    .document-properties {
        padding: 18px;
    }
    
    .properties-table th {
        width: 100px;
        font-size: 0.82em;
    }
    
    .properties-table th,
    .properties-table td {
        padding: 8px 10px;
    }
    
    .document-content {
        font-size: 15px;
    }
    
    .document-content h1 {
        font-size: 1.5em;
    }
    
    .document-content h2 {
        font-size: 1.3em;
    }
    
    .document-content h3 {
        font-size: 1.15em;
    }
    
    .code-block pre {
        padding: 16px 18px;
        font-size: 0.82em;
    }
    
    .table-wrapper {
        margin-left: -20px;
        margin-right: -20px;
        border-radius: 0;
        border-left: none;
        border-right: none;
    }
    
    .notion-table {
        font-size: 0.85em;
    }
    
    .notion-table th,
    .notion-table td {
        padding: 10px 8px;
    }
    
    .footer {
        flex-direction: column;
        align-items: flex-start;
        gap: 10px;
    }
}

@media (max-width: 480px) {
    .container {
        padding: 20px 15px;
    }
    
    .doc-title {
        font-size: 1.4em;
    }
    
    .metrics-bar {
        flex-direction: column;
        gap: 10px;
    }
    
    .document-content {
        font-size: 14px;
    }
    
    .code-block pre {
        font-size: 0.78em;
        padding: 14px;
    }
}

/* 打印样式 */
@media print {
    body {
        background: white;
        padding: 0;
    }
    
    .container {
        box-shadow: none;
        padding: 20px;
        max-width: 100%;
    }
    
    .metrics-bar,
    .footer {
        display: none;
    }
    
    .barcode {
        max-width: 200px;
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
        """Return CSS for homepage - Light theme with mobile support"""
        return """
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
    background: #fafafa;
    min-height: 100vh;
    padding: 15px;
}

/* 首页头部 - 简洁白色风格 */
.header {
    text-align: center;
    color: #1a1a1a;
    padding: 40px 20px 30px;
    background: white;
    border-radius: 12px 12px 0 0;
    margin: 0 auto;
    max-width: 1400px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.header h1 {
    font-size: 2.5em;
    font-weight: 600;
    margin-bottom: 8px;
    color: #2c3e50;
    letter-spacing: -0.5px;
}

.subtitle {
    font-size: 1em;
    color: #7f8c8d;
    font-weight: 400;
}

/* 主容器 */
.container {
    max-width: 1400px;
    margin: 0 auto;
    background: white;
    border-radius: 0 0 12px 12px;
    padding: 30px 40px 40px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

/* 统计区域 */
.stats {
    display: flex;
    gap: 30px;
    margin-bottom: 30px;
    padding-bottom: 25px;
    border-bottom: 1px solid #e8e8e8;
    flex-wrap: wrap;
}

.stat-item {
    text-align: center;
    flex: 1;
    min-width: 120px;
}

.stat-number {
    font-size: 2.2em;
    font-weight: 600;
    color: #3498db;
    background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.stat-label {
    font-size: 0.85em;
    color: #95a5a6;
    margin-top: 8px;
    font-weight: 500;
}

/* 表格容器 */
.table-container {
    overflow-x: auto;
    margin-bottom: 30px;
    border-radius: 8px;
    border: 1px solid #e8e8e8;
}

/* 文档表格 */
.doc-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.92em;
    min-width: 800px;
}

.doc-table thead {
    background: #f8f9fa;
    border-bottom: 2px solid #e0e0e0;
}

.doc-table th {
    padding: 14px 16px;
    text-align: left;
    font-weight: 600;
    color: #2c3e50;
    font-size: 0.85em;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    white-space: nowrap;
}

.doc-table td {
    padding: 16px;
    border-bottom: 1px solid #f0f0f0;
    color: #34495e;
}

.doc-table tbody tr {
    transition: background-color 0.2s ease;
}

.doc-table tbody tr:hover {
    background: #f8f9fa;
}

.doc-table tbody tr:last-child td {
    border-bottom: none;
}

/* 文档 ID 样式 */
.doc-id {
    font-family: "SF Mono", "Monaco", "Consolas", "Courier New", monospace;
    font-weight: 600;
    font-size: 0.9em;
    color: #7f8c8d;
}

.doc-id a {
    color: #3498db;
    text-decoration: none;
    transition: color 0.2s ease;
}

.doc-id a:hover {
    color: #2980b9;
    text-decoration: underline;
}

/* 文档标题 */
.doc-title {
    font-weight: 500;
    color: #2c3e50;
}

.doc-title a {
    color: #2c3e50;
    text-decoration: none;
    transition: color 0.2s ease;
}

.doc-title a:hover {
    color: #3498db;
}

/* 空状态 */
.empty-state {
    text-align: center;
    padding: 80px 20px !important;
    color: #bdc3c7;
    font-style: italic;
    font-size: 1.1em;
}

/* 分页 */
.pagination {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 8px;
    margin: 30px 0 20px;
    flex-wrap: wrap;
}

.page-link {
    padding: 8px 14px;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    text-decoration: none;
    color: #34495e;
    background: white;
    transition: all 0.2s ease;
    font-size: 0.9em;
    font-weight: 500;
}

.page-link:hover {
    background: #3498db;
    color: white;
    border-color: #3498db;
    transform: translateY(-1px);
}

.page-link.active {
    background: #3498db;
    color: white;
    border-color: #3498db;
    box-shadow: 0 2px 6px rgba(52, 152, 219, 0.3);
}

/* 页脚 */
.footer {
    margin-top: 40px;
    padding-top: 25px;
    border-top: 1px solid #e8e8e8;
    text-align: center;
    color: #95a5a6;
    font-size: 0.85em;
}

.footer p {
    margin: 6px 0;
}

.notice {
    color: #bdc3c7;
    font-style: italic;
}

/* ========== 移动端适配 ========== */

@media (max-width: 768px) {
    body {
        padding: 10px;
    }
    
    .header {
        padding: 25px 15px 20px;
        border-radius: 8px 8px 0 0;
    }
    
    .header h1 {
        font-size: 1.8em;
    }
    
    .subtitle {
        font-size: 0.9em;
    }
    
    .container {
        padding: 20px 15px 25px;
        border-radius: 0 0 8px 8px;
    }
    
    .stats {
        gap: 15px;
        padding-bottom: 20px;
    }
    
    .stat-item {
        min-width: 100px;
    }
    
    .stat-number {
        font-size: 1.8em;
    }
    
    .stat-label {
        font-size: 0.8em;
    }
    
    .table-container {
        margin-left: -15px;
        margin-right: -15px;
        border-radius: 0;
        border-left: none;
        border-right: none;
    }
    
    .doc-table {
        font-size: 0.85em;
    }
    
    .doc-table th,
    .doc-table td {
        padding: 10px 8px;
    }
    
    .doc-table th {
        font-size: 0.75em;
    }
    
    .pagination {
        gap: 6px;
    }
    
    .page-link {
        padding: 6px 10px;
        font-size: 0.85em;
    }
}

@media (max-width: 480px) {
    .header h1 {
        font-size: 1.5em;
    }
    
    .subtitle {
        font-size: 0.85em;
    }
    
    .stats {
        flex-direction: column;
        gap: 20px;
    }
    
    .stat-item {
        min-width: auto;
    }
    
    .doc-table th,
    .doc-table td {
        padding: 8px 6px;
    }
}

/* 平板适配 */
@media (min-width: 769px) and (max-width: 1024px) {
    .container {
        max-width: 95%;
    }
    
    .doc-table {
        font-size: 0.88em;
    }
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
