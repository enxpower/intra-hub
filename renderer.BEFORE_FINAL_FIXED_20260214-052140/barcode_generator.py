#!/usr/bin/env python3
"""
INTRA-HUB v1.0 - Barcode Generator
Generates Code128 barcodes for document identification
"""

import io
import base64
from pathlib import Path
from typing import Optional
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont


class BarcodeGenerator:
    """Generate Code128 barcodes for document IDs"""
    
    def __init__(self):
        self.output_dir = Path('/opt/intra-hub-v1.0/public/static/barcodes')
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_barcode_base64(self, doc_id: str) -> str:
        """
        Generate Code128 barcode and return as base64 data URI
        
        Args:
            doc_id: Document ID (e.g., "DOC-002029")
            
        Returns:
            Base64 data URI string for embedding in HTML
        """
        try:
            # Create Code128 barcode
            code128 = barcode.get_barcode_class('code128')
            
            # Generate barcode with custom options - high quality
            barcode_instance = code128(doc_id, writer=ImageWriter())
            
            # High-quality writer options for crisp, professional appearance
            writer_options = {
                'module_width': 0.35,      # Finer bars for higher detail
                'module_height': 8.0,      # Optimal height
                'quiet_zone': 3.5,         # Minimal margins
                'font_size': 10,           # Clean text size
                'text_distance': 5.0,      # Clear separation
                'background': 'white',
                'foreground': 'black',
                'write_text': True,        # Include human-readable text
                'text': doc_id,
                'dpi': 300,                # High DPI for crisp rendering
            }
            
            # Render to bytes
            buffer = io.BytesIO()
            barcode_instance.write(buffer, options=writer_options)
            buffer.seek(0)
            
            # Convert to base64
            img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
            data_uri = f"data:image/png;base64,{img_base64}"
            
            return data_uri
            
        except Exception as e:
            # Return placeholder on error
            return self._generate_text_placeholder(doc_id)
    
    def generate_barcode_file(self, doc_id: str) -> Optional[Path]:
        """
        Generate Code128 barcode and save to file
        
        Args:
            doc_id: Document ID
            
        Returns:
            Path to saved barcode image, or None on error
        """
        try:
            code128 = barcode.get_barcode_class('code128')
            barcode_instance = code128(doc_id, writer=ImageWriter())
            
            # Same high-quality options as base64 version
            writer_options = {
                'module_width': 0.35,
                'module_height': 8.0,
                'quiet_zone': 3.5,
                'font_size': 10,
                'text_distance': 5.0,
                'background': 'white',
                'foreground': 'black',
                'write_text': True,
                'text': doc_id,
                'dpi': 300,
            }
            
            filename = self.output_dir / f"{doc_id}"
            filepath = barcode_instance.save(str(filename), options=writer_options)
            
            return Path(filepath)
            
        except Exception as e:
            print(f"Error generating barcode for {doc_id}: {e}")
            return None
    
    def _generate_text_placeholder(self, doc_id: str) -> str:
        """Generate a simple text-based placeholder if barcode fails"""
        # Create simple image with text
        img = Image.new('RGB', (300, 80), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw border
        draw.rectangle([(0, 0), (299, 79)], outline='black', width=2)
        
        # Draw text (centered)
        text = f"ID: {doc_id}"
        bbox = draw.textbbox((0, 0), text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = ((300 - text_width) // 2, (80 - text_height) // 2)
        draw.text(position, text, fill='black')
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        
        return f"data:image/png;base64,{img_base64}"
    
    def get_barcode_html(self, doc_id: str, css_class: str = "barcode") -> str:
        """
        Generate HTML img tag for barcode
        
        Args:
            doc_id: Document ID
            css_class: CSS class for styling
            
        Returns:
            HTML img tag with embedded barcode
        """
        data_uri = self.generate_barcode_base64(doc_id)
        
        return f'''<img src="{data_uri}" alt="Barcode: {doc_id}" class="{css_class}" />'''


if __name__ == '__main__':
    # Test barcode generation
    generator = BarcodeGenerator()
    
    # Test with sample doc IDs
    for i in range(1, 4):
        doc_id = f"DOC-{i:04d}"
        print(f"Generating barcode for {doc_id}...")
        
        # Generate as file
        filepath = generator.generate_barcode_file(doc_id)
        if filepath:
            print(f"  Saved to: {filepath}")
        
        # Generate as base64
        data_uri = generator.generate_barcode_base64(doc_id)
        print(f"  Base64 length: {len(data_uri)} chars")
        
        # Generate HTML
        html = generator.get_barcode_html(doc_id)
        print(f"  HTML length: {len(html)} chars")
        print()
