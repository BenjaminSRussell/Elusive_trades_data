"""
OCR service using Tesseract with OCRmyPDF for scanned documents.
Combines image preprocessing with OCR for maximum accuracy.
"""

import pytesseract
import ocrmypdf
import logging
import tempfile
from pathlib import Path
from typing import Dict, Optional
import cv2
import numpy as np

from phase2_processing.ocr_pipeline.image_preprocessor import ImagePreprocessor

logger = logging.getLogger(__name__)


class OCRService:
    """
    OCR service for extracting text from scanned documents.
    Uses preprocessing pipeline for optimal accuracy.
    """

    def __init__(self, tesseract_cmd: Optional[str] = None):
        """
        Initialize OCR service.

        Args:
            tesseract_cmd: Path to tesseract executable (if not in PATH)
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        self.preprocessor = ImagePreprocessor()
        self.stats = {
            'processed': 0,
            'failed': 0,
            'total_chars': 0
        }

    def extract_text_from_image(self, image_path: str, preprocess: bool = True) -> Dict:
        """
        Extract text from a single image using Tesseract.

        Args:
            image_path: Path to image file
            preprocess: If True, apply preprocessing pipeline

        Returns:
            Dictionary with extracted text and confidence scores
        """
        try:
            if preprocess:
                # Apply preprocessing
                image = self.preprocessor.preprocess_image(image_path)
            else:
                # Load image directly
                image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

            if image is None:
                raise ValueError(f"Could not load image: {image_path}")

            # Extract text with detailed data
            ocr_data = pytesseract.image_to_data(
                image,
                output_type=pytesseract.Output.DICT,
                config='--psm 1'  # Automatic page segmentation with OSD
            )

            # Extract plain text
            text = pytesseract.image_to_string(
                image,
                config='--psm 1'
            )

            # Calculate average confidence
            confidences = [int(conf) for conf in ocr_data['conf'] if conf != '-1']
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            self.stats['processed'] += 1
            self.stats['total_chars'] += len(text)

            logger.info(f"OCR extracted {len(text)} chars with {avg_confidence:.1f}% confidence")

            return {
                'text': text,
                'confidence': avg_confidence,
                'word_count': len(text.split()),
                'char_count': len(text),
                'ocr_data': ocr_data
            }

        except Exception as e:
            self.stats['failed'] += 1
            logger.error(f"OCR failed for {image_path}: {e}")
            return {
                'text': '',
                'confidence': 0,
                'error': str(e)
            }

    def extract_text_from_pdf(self, pdf_path: str, output_pdf: Optional[str] = None) -> Dict:
        """
        Extract text from scanned PDF using OCRmyPDF.
        Creates a searchable PDF with embedded text layer.

        Args:
            pdf_path: Path to input PDF
            output_pdf: Path for output searchable PDF (optional)

        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            # Create temp output file if not specified
            if output_pdf is None:
                temp_output = tempfile.NamedTemporaryFile(
                    suffix='.pdf',
                    delete=False
                )
                output_pdf = temp_output.name

            # Run OCRmyPDF with optimized settings
            result = ocrmypdf.ocr(
                input_file=pdf_path,
                output_file=output_pdf,
                deskew=True,  # Automatically deskew pages
                clean=True,  # Clean background noise
                optimize=1,  # Optimize output PDF
                language='eng',
                force_ocr=False,  # Skip pages that already have text
                skip_text=False,
                redo_ocr=False,
                rotate_pages=True,  # Auto-rotate pages
                remove_background=True,
                unpaper_args='--layout double',
                progress_bar=False
            )

            # Extract text from the OCR'd PDF
            from phase2_processing.pdf_processor.pdf_extractor import PDFExtractor
            extractor = PDFExtractor()
            extracted = extractor.extract_from_file(output_pdf)

            self.stats['processed'] += 1
            self.stats['total_chars'] += len(extracted['text'])

            logger.info(f"OCR'd PDF: {len(extracted['text'])} chars extracted")

            return {
                'text': extracted['text'],
                'tables': extracted['tables'],
                'page_count': extracted['page_count'],
                'searchable_pdf_path': output_pdf,
                'ocrmypdf_result': result
            }

        except Exception as e:
            self.stats['failed'] += 1
            logger.error(f"OCRmyPDF failed for {pdf_path}: {e}")
            return {
                'text': '',
                'error': str(e)
            }

    def batch_process_images(self, image_paths: list) -> str:
        """
        Process multiple images and combine their text.

        Args:
            image_paths: List of image file paths

        Returns:
            Combined text from all images
        """
        all_text = []

        for image_path in image_paths:
            result = self.extract_text_from_image(image_path)
            if result['text']:
                all_text.append(result['text'])

        combined_text = '\n\n--- Page Break ---\n\n'.join(all_text)

        logger.info(f"Batch processed {len(image_paths)} images: {len(combined_text)} total chars")

        return combined_text


# Configuration for different document types
OCR_CONFIGS = {
    'spec_sheet': '--psm 1',  # Automatic page segmentation
    'table': '--psm 6',  # Uniform block of text
    'single_column': '--psm 4',  # Single column of text
    'single_word': '--psm 8',  # Single word
}


if __name__ == "__main__":
    # Test the OCR service
    logging.basicConfig(level=logging.INFO)
    ocr = OCRService()

    # Example usage
    # result = ocr.extract_text_from_image('scanned_page.png')
    # print(result['text'])
    # print(f"Confidence: {result['confidence']:.1f}%")
