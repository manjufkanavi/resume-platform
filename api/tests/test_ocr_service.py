"""Tests for OCR service (Tesseract-based).

Tests PDF/DOCX/image text extraction and edge cases.
Documents bugs found: OCR functions don't handle empty/None input.
"""

import pytest
import os
from unittest.mock import patch, MagicMock


class TestOCRService:
    """Test the OCR service module."""

    def test_ocr_service_import(self):
        """OCR service module should be importable."""
        try:
            from services.ocr import (
                extract_text_from_pdf,
                extract_text_from_docx,
                extract_text_from_image,
                extract_text_from_file,
                parse_text_to_json,
            )
            assert callable(extract_text_from_pdf)
            assert callable(extract_text_from_docx)
            assert callable(extract_text_from_image)
            assert callable(extract_text_from_file)
            assert callable(parse_text_to_json)
        except ImportError:
            pytest.skip("OCR service module not available")

    def test_extract_text_from_pdf_empty_bytes_raises(self):
        """BUG: extract_text_from_pdf raises on empty bytes.

        pypdf.errors.EmptyFileError: Cannot read an empty file

        Should return empty string or raise a handled exception.
        """
        try:
            from services.ocr import extract_text_from_pdf
        except ImportError:
            pytest.skip("OCR service module not available")

        with pytest.raises(Exception):
            extract_text_from_pdf(b"")

    def test_extract_text_from_pdf_none_raises(self):
        """BUG: extract_text_from_pdf raises on None.

        Should handle None gracefully, not crash.
        """
        try:
            from services.ocr import extract_text_from_pdf
        except ImportError:
            pytest.skip("OCR service module not available")

        with pytest.raises(Exception):
            extract_text_from_pdf(None)

    def test_extract_text_from_docx_empty_bytes_raises(self):
        """BUG: extract_text_from_docx raises on empty bytes."""
        try:
            from services.ocr import extract_text_from_docx
        except ImportError:
            pytest.skip("OCR service module not available")

        with pytest.raises(Exception):
            extract_text_from_docx(b"")

    def test_extract_text_from_image_empty_bytes(self):
        """extract_text_from_image returns '' when cv2/numpy unavailable."""
        try:
            from services.ocr import extract_text_from_image
        except ImportError:
            pytest.skip("OCR service module not available")

        result = extract_text_from_image(b"")
        assert result == ""

    def test_extract_text_from_file_pdf_empty(self):
        """BUG: extract_text_from_file raises on empty PDF bytes."""
        try:
            from services.ocr import extract_text_from_file
        except ImportError:
            pytest.skip("OCR service module not available")

        with pytest.raises(Exception):
            extract_text_from_file(b"", "pdf")

    def test_extract_text_from_file_docx_empty(self):
        """BUG: extract_text_from_file raises on empty DOCX bytes."""
        try:
            from services.ocr import extract_text_from_file
        except ImportError:
            pytest.skip("OCR service module not available")

        with pytest.raises(Exception):
            extract_text_from_file(b"", "docx")

    def test_extract_text_from_file_image_empty(self):
        """extract_text_from_file with image type returns '' when cv2 unavailable."""
        try:
            from services.ocr import extract_text_from_file
        except ImportError:
            pytest.skip("OCR service module not available")

        result = extract_text_from_file(b"", "image/png")
        assert result == ""

    def test_extract_text_from_file_unknown_type(self):
        """extract_text_from_file with unknown type returns ''."""
        try:
            from services.ocr import extract_text_from_file
        except ImportError:
            pytest.skip("OCR service module not available")

        result = extract_text_from_file(b"", "unknown")
        assert result == ""


class TestOCRWithMockedTesseract:
    """Test OCR service with mocked tesseract."""

    @patch("services.ocr.subprocess.run")
    def test_extract_text_success(self, mock_run):
        """Test successful text extraction with mocked tesseract."""
        try:
            from services.ocr import _ocr_with_tesseract
        except ImportError:
            pytest.skip("OCR service module not available")

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Extracted text from image",  # text=True means string
            stderr=""
        )

        result = _ocr_with_tesseract(b"fake_image_bytes")
        assert result == "Extracted text from image"
        mock_run.assert_called_once()

    @patch("services.ocr.subprocess.run")
    def test_extract_text_failure(self, mock_run):
        """Test failed text extraction with mocked tesseract."""
        try:
            from services.ocr import _ocr_with_tesseract
        except ImportError:
            pytest.skip("OCR service module not available")

        mock_run.side_effect = FileNotFoundError("tesseract not found")

        result = _ocr_with_tesseract(b"fake_image_bytes")
        assert result == ""

    @patch("services.ocr.subprocess.run")
    def test_extract_text_nonzero_returncode(self, mock_run):
        """Test extraction with non-zero return code."""
        try:
            from services.ocr import _ocr_with_tesseract
        except ImportError:
            pytest.skip("OCR service module not available")

        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",  # text=True means string
            stderr="Error processing file"
        )

        result = _ocr_with_tesseract(b"fake_image_bytes")
        assert result == ""


class TestParseTextToJson:
    """Test the text-to-JSON parser."""

    def test_parse_valid_json_text(self):
        """parse_text_to_json should parse valid JSON."""
        try:
            from services.ocr import parse_text_to_json
        except ImportError:
            pytest.skip("OCR service module not available")

        text = '{"name": "John", "email": "john@example.com"}'
        result = parse_text_to_json(text)
        assert isinstance(result, dict)

    def test_parse_empty_text(self):
        """parse_text_to_json should handle empty text."""
        try:
            from services.ocr import parse_text_to_json
        except ImportError:
            pytest.skip("OCR service module not available")

        result = parse_text_to_json("")
        assert isinstance(result, dict)

    def test_parse_invalid_json(self):
        """parse_text_to_json should handle invalid JSON gracefully."""
        try:
            from services.ocr import parse_text_to_json
        except ImportError:
            pytest.skip("OCR service module not available")

        result = parse_text_to_json("not valid json {{{")
        assert isinstance(result, dict)


class TestOCRServiceIntegration:
    """Integration tests for OCR service with real files."""

    def test_ocr_with_real_docx(self):
        """Test OCR with a real DOCX file if available."""
        try:
            from services.ocr import extract_text_from_docx
        except ImportError:
            pytest.skip("OCR service module not available")

        docx_paths = []
        for root, dirs, files in os.walk("."):
            for f in files:
                if f.endswith(".docx"):
                    docx_paths.append(os.path.join(root, f))
                    if len(docx_paths) >= 3:
                        break
            if len(docx_paths) >= 3:
                break

        if not docx_paths:
            pytest.skip("No DOCX files found in project")

        with open(docx_paths[0], "rb") as f:
            content = f.read()
        result = extract_text_from_docx(content)
        assert result is not None
        assert isinstance(result, str)
