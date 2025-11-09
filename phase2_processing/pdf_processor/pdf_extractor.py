"""
PDF text and table extraction using PyMuPDF (fitz).
High-performance extraction for digital-native PDFs with table support.
"""

import fitz  # PyMuPDF
import pikepdf
import hashlib
import logging
from typing import Optional, Dict, List
from pathlib import Path
from io import BytesIO

logger = logging.getLogger(__name__)


class PDFExtractor:
    """
    Extracts text and tables from PDF files using PyMuPDF.
    Handles corrupted PDFs using pikepdf for repair.
    """

    def __init__(self):
        self.stats = {
            'processed': 0,
            'repaired': 0,
            'failed': 0
        }

    def extract_from_file(self, pdf_path: str) -> Dict:
        """
        Extract text and tables from a PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with extracted content and metadata
        """
        try:
            doc = fitz.open(pdf_path)
            return self._extract_from_document(doc, pdf_path)
        except Exception as e:
            logger.warning(f"Failed to open PDF directly: {e}. Attempting repair...")
            return self._extract_with_repair(pdf_path)

    def extract_from_bytes(self, pdf_bytes: bytes) -> Dict:
        """
        Extract text and tables from PDF bytes.

        Args:
            pdf_bytes: PDF file as bytes

        Returns:
            Dictionary with extracted content and metadata
        """
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            return self._extract_from_document(doc, source='bytes')
        except Exception as e:
            logger.warning(f"Failed to open PDF from bytes: {e}. Attempting repair...")
            return self._extract_with_repair_bytes(pdf_bytes)

    def _extract_from_document(self, doc: fitz.Document, source: str) -> Dict:
        """
        Core extraction logic for a PyMuPDF document.

        Args:
            doc: fitz.Document object
            source: Source identifier (file path or 'bytes')

        Returns:
            Dictionary with extracted data
        """
        result = {
            'text': '',
            'tables': [],
            'metadata': {},
            'page_count': len(doc),
            'is_scanned': False,
            'file_size_bytes': 0,
            'document_hash': '',
        }

        all_text = []
        all_tables = []

        # Extract from each page
        for page_num in range(len(doc)):
            page = doc[page_num]

            # Extract text
            page_text = page.get_text()
            all_text.append(page_text)

            # Check if page is scanned (no extractable text but has images)
            if len(page_text.strip()) < 50 and len(page.get_images()) > 0:
                result['is_scanned'] = True

            # Extract tables using PyMuPDF's table detection
            try:
                tables = page.find_tables()
                for table in tables:
                    # Extract table as list of lists
                    table_data = table.extract()
                    if table_data:
                        all_tables.append({
                            'page': page_num + 1,
                            'data': table_data,
                            'bbox': table.bbox  # Bounding box coordinates
                        })
            except Exception as e:
                logger.debug(f"Table extraction failed for page {page_num + 1}: {e}")

        # Combine all text
        result['text'] = '\n\n'.join(all_text)
        result['tables'] = all_tables

        # Extract metadata
        result['metadata'] = {
            'title': doc.metadata.get('title', ''),
            'author': doc.metadata.get('author', ''),
            'subject': doc.metadata.get('subject', ''),
            'creator': doc.metadata.get('creator', ''),
        }

        # Calculate hash
        result['document_hash'] = hashlib.sha256(result['text'].encode()).hexdigest()

        # File size
        if isinstance(source, str) and source != 'bytes':
            result['file_size_bytes'] = Path(source).stat().st_size

        doc.close()

        self.stats['processed'] += 1
        logger.info(f"Extracted {len(result['text'])} chars, {len(all_tables)} tables from {source}")

        return result

    def _extract_with_repair(self, pdf_path: str) -> Dict:
        """
        Attempt to repair a corrupted PDF using pikepdf and then extract.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with extracted data
        """
        try:
            # Repair PDF with pikepdf
            repaired_pdf = BytesIO()
            with pikepdf.open(pdf_path) as pdf:
                pdf.save(repaired_pdf)

            repaired_pdf.seek(0)
            self.stats['repaired'] += 1

            # Try extraction again
            doc = fitz.open(stream=repaired_pdf.read(), filetype="pdf")
            return self._extract_from_document(doc, source=f'{pdf_path} (repaired)')

        except Exception as e:
            self.stats['failed'] += 1
            logger.error(f"Failed to extract from {pdf_path} even after repair: {e}")
            return {
                'text': '',
                'tables': [],
                'metadata': {},
                'error': str(e),
                'is_scanned': True  # Assume it might need OCR
            }

    def _extract_with_repair_bytes(self, pdf_bytes: bytes) -> Dict:
        """
        Attempt to repair a corrupted PDF from bytes.

        Args:
            pdf_bytes: PDF as bytes

        Returns:
            Dictionary with extracted data
        """
        try:
            input_pdf = BytesIO(pdf_bytes)
            repaired_pdf = BytesIO()

            with pikepdf.open(input_pdf) as pdf:
                pdf.save(repaired_pdf)

            repaired_pdf.seek(0)
            self.stats['repaired'] += 1

            doc = fitz.open(stream=repaired_pdf.read(), filetype="pdf")
            return self._extract_from_document(doc, source='bytes (repaired)')

        except Exception as e:
            self.stats['failed'] += 1
            logger.error(f"Failed to extract from bytes even after repair: {e}")
            return {
                'text': '',
                'tables': [],
                'metadata': {},
                'error': str(e),
                'is_scanned': True
            }

    def extract_images(self, pdf_path: str, output_dir: str) -> List[str]:
        """
        Extract all images from a PDF for OCR processing.

        Args:
            pdf_path: Path to PDF file
            output_dir: Directory to save extracted images

        Returns:
            List of paths to extracted images
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        image_paths = []

        try:
            doc = fitz.open(pdf_path)

            for page_num in range(len(doc)):
                page = doc[page_num]
                images = page.get_images()

                for img_index, img in enumerate(images):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]

                    # Save image
                    image_filename = f"page_{page_num + 1}_img_{img_index + 1}.png"
                    image_path = output_path / image_filename

                    with open(image_path, "wb") as img_file:
                        img_file.write(image_bytes)

                    image_paths.append(str(image_path))

            doc.close()
            logger.info(f"Extracted {len(image_paths)} images from {pdf_path}")

        except Exception as e:
            logger.error(f"Image extraction failed: {e}")

        return image_paths


if __name__ == "__main__":
    # Test the extractor
    logging.basicConfig(level=logging.INFO)
    extractor = PDFExtractor()

    # Example usage
    # result = extractor.extract_from_file('sample.pdf')
    # print(f"Extracted {len(result['text'])} characters")
    # print(f"Found {len(result['tables'])} tables")
