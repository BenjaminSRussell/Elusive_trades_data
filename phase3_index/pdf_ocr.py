"""PDF text extract with optional OCR fallback for scanned pages (#6)."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


def extract_text_native(pdf_path: Path) -> str:
    """Try pypdf / PyPDF2 native text extraction."""
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError:
            return ""
    try:
        reader = PdfReader(str(pdf_path))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts).strip()
    except Exception as exc:
        logger.warning("native PDF extract failed: %s", exc)
        return ""


def ocr_pdf(pdf_path: Path, *, lang: str = "eng") -> str:
    """OCR via pdf2image + pytesseract when available."""
    try:
        from pdf2image import convert_from_path  # type: ignore
        import pytesseract  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "OCR requires pdf2image + pytesseract (+ poppler). "
            "pip install pdf2image pytesseract"
        ) from exc
    images = convert_from_path(str(pdf_path))
    texts = [pytesseract.image_to_string(img, lang=lang) for img in images]
    return "\n".join(texts).strip()


def extract_with_ocr_fallback(
    pdf_path: Path | str,
    *,
    min_chars: int = 40,
    force_ocr: bool = False,
) -> Tuple[str, str]:
    """Return (text, source) where source is 'native' or 'ocr'.

    Native-text PDFs skip OCR when extracted length >= min_chars.
    """
    path = Path(pdf_path)
    if not force_ocr:
        native = extract_text_native(path)
        if len(native) >= min_chars:
            return native, "native"
    try:
        ocr_text = ocr_pdf(path)
        return ocr_text, "ocr"
    except RuntimeError:
        # OCR deps missing — return whatever native gave
        native = extract_text_native(path)
        return native, "native" if native else "empty"


def ingest_pdf_to_index(
    pdf_path: Path | str,
    index,
    *,
    part_numbers: Optional[List[str]] = None,
) -> dict:
    """Extract text (OCR if needed) and store page text with source flag."""
    path = Path(pdf_path)
    text, source = extract_with_ocr_fallback(path)
    doc_id = index.upsert_document(str(path), title=path.name)
    page_id = index.add_page(doc_id, 1, text=text)
    # Stash source on description of a synthetic part or page — extend via parts
    n_parts = 0
    for pn in part_numbers or []:
        index.add_part(doc_id, pn, description=f"source={source}", page_ref=1, page_id=page_id)
        n_parts += 1
    return {"document_id": doc_id, "source": source, "chars": len(text), "parts": n_parts}
