"""Real end-to-end OCR test (Phase 2.7).

Generates a *scanned*-style sample PDF (text rendered to an image with no text
layer), then runs the actual resume-api OCR pipeline end-to-end:

    extract_text_from_file(...) -> parse_text_to_json(...) -> ATS scoring

This exercises the real local tesseract OCR engine (no mocking of the OCR
logic), verifying that a sample PDF produces real, parseable structured output.
"""
import io
import shutil

import pytest
from pypdf import PdfReader

from services.ocr import extract_text_from_file, parse_text_to_json

SAMPLE_LINES = [
    "Summary: Senior software engineer.",
    "Focused on building scalable microservices.",
    "Experience: Built microservices, 90% faster.",
    "Led distributed engineering teams.",
    "Skills: Python, Docker, Kubernetes.",
    "Open source contributor and mentor.",
    "Education: BS Computer Science.",
    "Specialized in distributed systems.",
]


def _make_scanned_pdf(text_lines, font_size=30, width=960):
    """Render text lines onto an image and save as a PDF with NO text layer."""
    from PIL import Image, ImageDraw, ImageFont

    font_path = "/System/Library/Fonts/Geneva.ttf"
    height = max(len(text_lines) * 72, 520)
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, font_size)
    y = font_size + 15
    for line in text_lines:
        draw.text((30, y), line, fill="black", font=font)
        y += font_size + 42
    buf = io.BytesIO()
    img.save(buf, "PDF")
    return buf.getvalue()


def _tesseract_available():
    return shutil.which("tesseract") is not None


@pytest.mark.skipif(not _tesseract_available(), reason="tesseract binary not installed")
def test_scanned_pdf_ocr_end_to_end():
    pdf_bytes = _make_scanned_pdf(SAMPLE_LINES)

    # Sanity: pypdf extracts NO text (this is a scanned page with no text layer).
    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert not (reader.pages[0].extract_text() or "").strip()

    # Real OCR pipeline: scanned PDF -> tesseract -> structured sections.
    text = extract_text_from_file(pdf_bytes, "application/pdf")
    parsed = parse_text_to_json(text)
    sections = parsed["sections"]

    # Real text was extracted (not empty, not a stub).
    assert text.strip(), "OCR extracted no text"
    low = text.lower()
    # Key resume content survived OCR (allowing minor noise).
    assert "software engineer" in low
    assert "microservice" in low
    assert "python" in low and "docker" in low

    # Sections were structured by the parser.
    assert "summary" in sections
    assert "experience" in sections
    assert "skills" in sections
    assert "education" in sections

    # ATS scoring runs on the extracted text and yields a non-trivial score.
    from services.ats import calculate_ats_score

    score = calculate_ats_score(parsed, "software engineer")["overall"]
    assert 30 <= score <= 100, f"expected a meaningful score, got {score}"


@pytest.mark.skipif(not _tesseract_available(), reason="tesseract binary not installed")
def test_text_based_pdf_still_works():
    """A text-layered PDF should extract via pypdf (no OCR needed)."""
    from PIL import Image, ImageDraw, ImageFont

    font_path = "/System/Library/Fonts/Geneva.ttf"
    img = Image.new("RGB", (960, 400), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, 28)
    y = 30
    for line in SAMPLE_LINES:
        draw.text((30, y), line, fill="black", font=font)
        y += 66
    buf = io.BytesIO(); img.save(buf, "PDF")

    text = extract_text_from_file(buf.getvalue(), "application/pdf")
    assert "software engineer" in text.lower()
    assert "microservices" in text.lower()
