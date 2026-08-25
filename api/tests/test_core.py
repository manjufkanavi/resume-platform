"""Core-logic tests for the resume platform (deterministic, no external services).

Covers Phase 1 tasks:
  - 1.2 database models (via pydantic response models)
  - ATS scoring engine (services/ats.py)
  - OCR text parsing + docx extraction (services/ocr.py)
  - LLM improvement generation fallback (services/llm.py)
  - pydantic request/response models (models.py)
"""
import io

import pytest
from docx import Document

from services.ats import calculate_ats_score, _calculate_keyword_match
from services.ocr import (
    parse_text_to_json,
    extract_text_from_docx,
    extract_text_from_image,
    extract_text_from_file,
)
from services.llm import _get_fallback_improvements
from models import ATSScore, UploadResponse, ResumeStatus


# ── Helpers ──────────────────────────────────────────────────────────────

COMPLETE_OCR = {
    "sections": {
        "contact_info": "Contact: john@example.com Phone 555-0100 LinkedIn in/john",
        "summary": "Summary: Senior software engineer with 8 years experience",
        "experience": "- Built and deployed scalable microservices. Work led to 90% latency reduction.",
        "education": "Education: B.S. in Computer Science, Bachelor of Science",
        "skills": "Skills: Python, Docker, Kubernetes, AWS, Terraform",
    },
    "raw_text": (
        "john@example.com\nSenior software engineer\n"
        "Built and deployed scalable microservices.\n"
        "B.S. in Computer Science\nPython, Docker, Kubernetes"
    ),
    "word_count": 300,
    "line_count": 8,
}

SPARSE_OCR = {
    "sections": {"experience": "Built some services"},
    "raw_text": "Built some services today now",
    "word_count": 20,
    "line_count": 1,
}


def _serialize_docx(*paragraphs):
    """Serialize a python-docx Document to bytes (works across docx versions)."""
    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ── ATS scoring (1.2 / pipeline) ─────────────────────────────────────────

def test_complete_resume_scores_high():
    score = calculate_ats_score(COMPLETE_OCR, "software engineer")["overall"]
    # A well-formed resume with all sections + job title should score well.
    assert 50 <= score <= 100, f"complete resume score out of range: {score}"


def test_complete_outperforms_sparse_resume():
    complete = calculate_ats_score(COMPLETE_OCR, "software engineer")["overall"]
    sparse = calculate_ats_score(SPARSE_OCR, "software engineer")["overall"]
    assert complete > sparse


def test_scores_always_bounded_0_to_100():
    for ocr in (COMPLETE_OCR, SPARSE_OCR, {"sections": {}, "raw_text": ""},
                {"sections": {"experience": "x" * 5000}, "raw_text": "x" * 5000}):
        score = calculate_ats_score(ocr, "devops engineer")
        assert 0 <= score["overall"] <= 100
        assert 0 <= score["keywords_match"] <= 100
        assert 0 <= score["completeness"] <= 100


def test_no_job_title_is_neutral_on_keywords():
    score, missing = _calculate_keyword_match(
        "I built services and deployed them", None
    )
    assert score == 50
    assert missing == []


def test_keyword_match_reports_missing_terms():
    # "python developer" matches the software industry pool, so missing terms
    # (python, docker, ...) that are absent from the resume text are reported.
    score, missing = _calculate_keyword_match(
        "I write application code and run tests daily", "python developer"
    )
    assert score < 50
    assert "python" in missing
    assert "docker" in missing


# ── OCR parsing (1.4 pipeline) ───────────────────────────────────────────

def test_parse_detects_standard_sections():
    # Body lines after each header are what get saved into sections.
    text = (
        "Experience:\n"
        "Built scalable microservices achieving 90% latency reduction.\n"
        "Led a cross-functional team of engineers.\n"
        "Skills:\n"
        "Python, Docker, Kubernetes, AWS, Terraform.\n"
        "Education:\n"
        "Completed studies focused on distributed systems.\n"
        "Summary: Senior software engineer.\n"
    )
    parsed = parse_text_to_json(text)
    sections = parsed["sections"]
    assert "experience" in sections
    assert "skills" in sections
    assert "education" in sections
    assert parsed["word_count"] > 0


def test_parse_falls_back_to_raw_text():
    parsed = parse_text_to_json("just plain text with no section headers here")
    assert "raw_text" in parsed
    assert parsed["raw_text"].strip()


def test_extract_text_from_docx():
    blob = _serialize_docx(
        "Experience: Built microservices achieving 40% faster delivery",
        "Skills: Python and Docker",
        "Education: BS Computer Science",
    )
    text = extract_text_from_docx(blob)
    assert "Built microservices" in text
    assert "Python" in text


def test_extract_text_from_file_routes_by_type():
    blob = _serialize_docx("Experience: Built things", "Skills: Python")
    text = extract_text_from_file(
        blob, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert "Built things" in text


def test_image_ocr_returns_string_even_when_unavailable():
    # When cv2/numpy/surya are missing this returns "" (a string); when present it
    # attempts extraction. Either way the contract is "return a str".
    out = extract_text_from_image(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x00fake")
    assert isinstance(out, str)


# ── LLM fallback (1.4 pipeline) ──────────────────────────────────────────

def test_fallback_improvements_structure():
    fb = _get_fallback_improvements({"overall": 42, "recommendations": ["Add a summary"]})
    assert "rewritten_sections" in fb
    assert "suggestions" in fb and isinstance(fb["suggestions"], list)
    assert "keyword_suggestions" in fb
    assert "formatting_tips" in fb
    assert isinstance(fb["estimated_ats_score_after"], int)
    assert fb["estimated_ats_score_after"] >= 42  # +15 clamped to 100


def test_fallback_high_score_still_clamped():
    fb = _get_fallback_improvements({"overall": 95, "recommendations": []})
    assert fb["estimated_ats_score_after"] <= 100


# ── Pydantic models (1.2 / response contracts) ───────────────────────────

def test_ats_score_model_bounds_enforced():
    good = ATSScore(overall=55, keywords_match=60, formatting=70,
                    completeness=80, section_scores={}, missing_keywords=[],
                    recommendations=[])
    assert good.overall == 55
    with pytest.raises(ValueError):
        ATSScore(overall=150, keywords_match=0, formatting=0,
                 completeness=0, section_scores={}, missing_keywords=[],
                 recommendations=[])


def test_upload_response_model():
    resp = UploadResponse(resume_id="abc-123", status=ResumeStatus.PROCESSING,
                          message="ok")
    assert resp.resume_id == "abc-123"
    assert resp.status == ResumeStatus.PROCESSING


def test_resume_status_enum_values():
    assert ResumeStatus.PENDING == "pending"
    assert ResumeStatus.COMPLETED == "completed"
    assert ResumeStatus.FAILED == "failed"
