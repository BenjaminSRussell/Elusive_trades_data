"""OCR fallback skips native-text PDFs (#6)."""
from __future__ import annotations

from pathlib import Path
from unittest import mock

from phase3_index.pdf_ocr import extract_with_ocr_fallback


def test_native_text_skips_ocr(tmp_path: Path):
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    long = "word " * 50
    with mock.patch("phase3_index.pdf_ocr.extract_text_native", return_value=long):
        with mock.patch("phase3_index.pdf_ocr.ocr_pdf") as ocr:
            text, source = extract_with_ocr_fallback(pdf)
            ocr.assert_not_called()
            assert source == "native"
            assert "word" in text


def test_empty_native_attempts_ocr(tmp_path: Path):
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF")
    with mock.patch("phase3_index.pdf_ocr.extract_text_native", return_value=""):
        with mock.patch("phase3_index.pdf_ocr.ocr_pdf", return_value="SERIAL 0131M00008P"):
            text, source = extract_with_ocr_fallback(pdf)
            assert source == "ocr"
            assert "0131M00008P" in text
