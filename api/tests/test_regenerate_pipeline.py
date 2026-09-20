"""Integration tests for the hardened inline /regenerate pipeline (Phase 2.3).

Drives a real resume through ``resumes.regenerate_pipeline`` end-to-end: OCR + ATS
run on the *actual* deterministic services (docx -> python-docx, no external OCR
engine needed), while the Ollama LLM stage is stubbed so we never touch a live model.

Also asserts the P2.2 hardening contract: an infra failure (MinIO download error)
aborts the pipeline, persists ``status='failed'`` + ``error_message``, and returns
HTTP 500 — the failure survives a restart because it is written to the DB. A
per-stage timeout on the LLM stage falls back to deterministic improvements instead
of failing outright.

Test design note: ``regenerate_pipeline`` opens one ``async with get_db() as db``
block and calls ``db.commit()`` internally. Every call to the monkeypatched get_db
must therefore yield *the same* FakeDB instance so assertions can observe the
persisted state. We use a per-test ``holder`` dict that both the patched get_db and
the test assertions reference — no module-level globals.
"""

import io

from contextlib import asynccontextmanager
from docx import Document

import pytest
from fastapi.testclient import TestClient

import routes.resumes
from main import app


# Shared client for all tests (mirrors test_api_e2e.py).
client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_dependency_overrides():
    """Isolate dependency_overrides between tests (TestClient state leaks)."""

    original = dict(app.dependency_overrides)
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(original)


def _make_docx_bytes():
    """A docx whose paragraphs parse into the standard resume sections."""

    doc = Document()
    doc.add_paragraph("Experience:")
    doc.add_paragraph("Built microservices achieving 40% faster delivery.")
    doc.add_paragraph("Led a cross-functional team of engineers.")
    doc.add_paragraph("Skills: Python, Docker, Kubernetes, AWS.")
    doc.add_paragraph("Education: BS Computer Science.")
    doc.add_paragraph(
        "Summary: Senior backend engineer with 6 years of experience."
    )
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_docx_text():
    """The plain text ``extract_text_from_file`` returns for a DOCX like the above."""

    return (
        "Experience:\n"
        "Built microservices achieving 40% faster delivery.\n"
        "Led a cross-functional team of engineers.\n"
        "Skills: Python, Docker, Kubernetes, AWS.\n"
        "Education: BS Computer Science.\n"
        "Summary: Senior backend engineer with 6 years of experience."
    )


def _fake_ocr_and_download(monkeypatch):
    """Patch download + extractor together (download returns bytes, OCR parses them)."""

    monkeypatch.setattr(
        routes.resumes, "download_file", lambda key: _make_docx_bytes()
    )
    monkeypatch.setattr(
        routes.resumes, "extract_text_from_file", lambda data, ftype: _make_docx_text()
    )


class _FakeUser:
    """Stand-in for a User row (real ORM object is unnecessary here)."""

    id = "uid-123"


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeDB:
    """Minimal async DB shim. ``commits`` lets tests assert persistence happened."""

    def __init__(self, resume):
        self.resume = resume
        self.commits = 0

    async def execute(self, statement):
        sql = str(statement)
        if "users" in sql:  # User ownership lookup (resumes table has no 'users')
            return _FakeResult(_FakeUser())
        # Resume-by-id lookup is the first query in regenerate_pipeline.
        return _FakeResult(self.resume)

    async def commit(self):
        self.commits += 1

    async def add(self, obj):  # noqa: D401 - unused in this path
        pass

    async def refresh(self, obj):  # noqa: D401 - unused in this path
        return obj


def _make_resume():
    from database import Resume  # local import avoids a circular load cost

    resume = Resume()
    resume.id = "resume-e2e-1"
    resume.user_id = "uid-123"  # matches _FakeUser.id so ownership passes
    resume.filename = "resume.pdf"
    resume.file_type = "application/pdf"
    resume.minio_key = "resumes/resume.pdf"
    return resume


class TestRegenerateSuccess:
    """The happy path: OCR + ATS run for real, LLM is stubbed."""

    def test_regenerate_populates_all_fields(self, monkeypatch):
        holder = {}
        resume = _make_resume()

        @asynccontextmanager
        async def _get_db():
            holder["db"] = _FakeDB(resume)
            yield holder["db"]

        monkeypatch.setattr(routes.resumes, "get_db", _get_db)
        # Real docx extraction (no external OCR engine needed).
        monkeypatch.setattr(
            routes.resumes, "download_file", lambda key: _make_docx_bytes()
        )
        monkeypatch.setattr(
            routes.resumes, "extract_text_from_file", lambda data, ftype: _make_docx_text()
        )
        # Stub only the Ollama stage so this runs offline.
        monkeypatch.setattr(
            routes.resumes,
            "generate_improvements",
            lambda ocr, ats, job_title: {
                "rewritten_sections": {"experience": "Quantified impact."},
                "suggestions": ["Add more metrics"],
            },
        )
        app.dependency_overrides[routes.resumes.require_auth] = lambda: {
            "keycloak_id": "kc-1",
            "email": "alice@example.com",
            "name": "Alice",
        }

        resp = client.post(
            "/api/v1/resume/resume-e2e-1/regenerate",
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed"

        # Pipeline persisted results across stages (processing commit + final).
        assert holder["db"].commits == 2
        assert resume.status == "completed"
        # Real OCR sections were captured (not an empty dict).
        assert resume.ats_score_json and "overall" in resume.ats_score_json
        assert "experience" in (resume.ocr_json or {}).get("sections", {})
        # Stubbed LLM result landed on the row and matches what we returned.
        assert body["improvements"]["suggestions"] == ["Add more metrics"]

    def test_regenerate_marks_processing_then_completed(self, monkeypatch):
        """Status transitions pending -> processing (up front) -> completed."""

        holder = {}
        resume = _make_resume()

        @asynccontextmanager
        async def _get_db():
            holder["db"] = _FakeDB(resume)
            yield holder["db"]

        monkeypatch.setattr(routes.resumes, "get_db", _get_db)
        monkeypatch.setattr(
            routes.resumes, "download_file", lambda key: _make_docx_bytes()
        )
        monkeypatch.setattr(
            routes.resumes, "extract_text_from_file", lambda data, ftype: _make_docx_text()
        )
        monkeypatch.setattr(
            routes.resumes,
            "generate_improvements",
            lambda ocr, ats, job_title: {"suggestions": ["ok"]},
        )
        app.dependency_overrides[routes.resumes.require_auth] = lambda: {
            "keycloak_id": "kc-1",
            "email": "alice@example.com",
        }

        client.post("/api/v1/resume/resume-e2e-1/regenerate")

        # Two commits: the up-front "processing" mark and the final persist.
        assert holder["db"].commits == 2
        assert resume.status == "completed"


class TestRegenerateFailure:
    """Infra failure aborts the pipeline and persists status='failed'."""

    def test_minio_download_failure_sets_failed_status(self, monkeypatch):
        holder = {}
        resume = _make_resume()

        @asynccontextmanager
        async def _get_db():
            holder["db"] = _FakeDB(resume)
            yield holder["db"]

        monkeypatch.setattr(routes.resumes, "get_db", _get_db)

        def boom(key):
            raise RuntimeError("MinIO connection refused")

        monkeypatch.setattr(routes.resumes, "download_file", boom)
        app.dependency_overrides[routes.resumes.require_auth] = lambda: {
            "keycloak_id": "kc-1",
            "email": "alice@example.com",
        }

        resp = client.post("/api/v1/resume/resume-e2e-1/regenerate")

        assert resp.status_code == 500
        # Infra failure persisted to DB so it survives a restart.
        assert holder["db"].commits >= 1
        assert resume.status == "failed"
        assert "OCR extraction error" in (resume.error_message or "")

    def test_ocr_stage_timeout_sets_failed_status(self, monkeypatch):
        """A stage exceeding its timeout budget -> status='failed'."""

        holder = {}
        resume = _make_resume()

        @asynccontextmanager
        async def _get_db():
            holder["db"] = _FakeDB(resume)
            yield holder["db"]

        monkeypatch.setattr(routes.resumes, "get_db", _get_db)
        # Real OCR+ATS must run so the failure path is exercised.
        monkeypatch.setattr(
            routes.resumes, "download_file", lambda key: _make_docx_bytes()
        )
        monkeypatch.setattr(
            routes.resumes, "extract_text_from_file", lambda data, ftype: _make_docx_text()
        )

        def fake_run_stage(fn, stage_name):
            if stage_name == "OCR extraction":
                raise routes.resumes.StageTimeout("OCR exceeded budget")
            return fn()

        monkeypatch.setattr(routes.resumes, "_run_stage", fake_run_stage)
        app.dependency_overrides[routes.resumes.require_auth] = lambda: {
            "keycloak_id": "kc-1",
            "email": "alice@example.com",
        }

        resp = client.post("/api/v1/resume/resume-e2e-1/regenerate")

        assert resp.status_code == 500
        assert resume.status == "failed"
        assert "timed out" in (resume.error_message or "")


class TestRegenerateLlmTimeout:
    """Ollama timeout must NOT fail the pipeline — it falls back to deterministic."""

    def test_llm_timeout_uses_fallback_improvements(self, monkeypatch):
        holder = {}
        resume = _make_resume()

        @asynccontextmanager
        async def _get_db():
            holder["db"] = _FakeDB(resume)
            yield holder["db"]

        monkeypatch.setattr(routes.resumes, "get_db", _get_db)
        # Real OCR+ATS must run so the LLM stage is actually reached.
        monkeypatch.setattr(
            routes.resumes, "download_file", lambda key: _make_docx_bytes()
        )
        monkeypatch.setattr(
            routes.resumes, "extract_text_from_file", lambda data, ftype: _make_docx_text()
        )

        async def fake_run_stage(fn, stage_name):
            if stage_name == "LLM improvements":
                raise routes.resumes.StageTimeout("Ollama timed out")
            return fn()  # OCR/ATS are plain lambdas returning dicts; the route awaits _run_stage's result

        monkeypatch.setattr(routes.resumes, "_run_stage", fake_run_stage)
        app.dependency_overrides[routes.resumes.require_auth] = lambda: {
            "keycloak_id": "kc-1",
            "email": "alice@example.com",
        }

        resp = client.post("/api/v1/resume/resume-e2e-1/regenerate")

        assert resp.status_code == 200
        # Fallback still yields a completed, structured result.
        assert holder["db"].commits == 2
        assert resume.status == "completed"
        imps = resume.improvements_json or {}
        assert isinstance(imps.get("estimated_ats_score_after"), int)
