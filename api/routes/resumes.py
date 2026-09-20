"""Resume routes — CRUD, upload, scoring, improvements."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from concurrent.futures import TimeoutError as StageTimeout
from datetime import datetime, timezone
from typing import Any, Callable, NoReturn, TypeVar

T = TypeVar("T")
from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, File, Form
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from database import Resume, User, get_db
from models import (
    ResumeResult,
    UploadResponse,
    ScoreResponse,
    ImprovementResponse,
    ListResumesResponse,
    DeleteResponse,
    ListResumeItem,
    ResumeStatus,
)
from services.ocr import extract_text_from_file, parse_text_to_json
from services.ats import calculate_ats_score
from services.llm import generate_improvements, _get_fallback_improvements
from services.minio import upload_file, delete_file, download_file
from services.auth import get_user_from_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/resume", tags=["resumes"])

MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", "10")) * 1024 * 1024

# ── Inline pipeline timeout budget (seconds) ───────────────────────────────
# Each stage of regenerate_pipeline runs in a worker thread with its own budget so
# one slow/hung external call (MinIO, OCR engine, Ollama) cannot hang the request
# forever. A stage that exceeds its budget is treated as a failure and the resume
# status transitions to "failed" with an explanatory error_message (persisted).
PIPELINE_TIMEOUT_SECONDS = int(os.getenv("PIPELINE_TIMEOUT_SECONDS", "180"))


async def require_auth(authorization: str = Header(default="Bearer ")) -> dict:
    """Dependency: extract and validate Bearer token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]
    user = await get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=201,
)
async def upload_resume(
    file: UploadFile = File(...),
    job_title: str = Form(None),
    experience_years: int = Form(None),
    user: dict = Depends(require_auth),
):
    """Upload a resume file for processing.

    A submission is identified by the authenticated user's email plus the
    submitted resume filename (the "application"). Re-submitting the same
    application returns HTTP 409 Conflict instead of silently creating a
    duplicate record or raising an unhandled DB error (500).
    """
    # Validate file size
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large (max {MAX_FILE_SIZE // 1024 // 1024}MB)")

    # Validate file type
    allowed_types = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/png",
        "image/jpeg",
        "image/jpg",
    }
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Unsupported file type. Allowed: PDF, DOCX, JPG, PNG")

    original_filename = file.filename or "resume"

    async with get_db() as db:
        # Get or create user
        result = await db.execute(
            select(User).where(User.keycloak_id == user.get("keycloak_id"))
        )
        db_user = result.scalar_one_or_none()

        if not db_user:
            db_user = User(
                id=uuid.uuid4(),
                keycloak_id=user.get("keycloak_id"),
                email=user.get("email"),
                name=user.get("name"),
            )
            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)

        # Duplicate detection: same user + same resume filename. Checked before
        # any MinIO write so a duplicate is rejected cheaply with 409 instead of
        # creating another record or raising an unhandled DB error (500).
        dup = await db.execute(
            select(Resume).where(
                Resume.user_id == db_user.id,
                Resume.filename == original_filename,
            )
        )
        if dup.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=409,
                detail="Application already exists for this email and name",
            )

        # Generate unique filename + upload to MinIO
        file_id = str(uuid.uuid4())
        safe_filename = f"{file_id}_{original_filename}"

        try:
            minio_key = upload_file(file_content, safe_filename, file.content_type)
        except Exception as e:
            logger.error(f"MinIO upload failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload file")

        # Create resume record
        try:
            resume = Resume(
                user_id=db_user.id,
                filename=original_filename,
                file_type=file.content_type,
                file_size=len(file_content),
                minio_key=minio_key,
                status=ResumeStatus.PROCESSING,
                job_title=job_title,
                experience_years=experience_years,
            )
            db.add(resume)
            await db.commit()
            await db.refresh(resume)
        except IntegrityError as e:
            # A concurrent insert slipped past the pre-check above. Treat a
            # duplicate application as 409 Conflict, not an unhandled 500.
            logger.warning(f"Duplicate application rejected: {e}")
            raise HTTPException(
                status_code=409,
                detail="Application already exists for this email and name",
            )

    return UploadResponse(
        resume_id=str(resume.id),
        status=ResumeStatus.PROCESSING,
        message="Resume uploaded successfully. Processing started.",
    )


@router.get("/", response_model=ListResumesResponse)
async def list_resumes(
    user: dict = Depends(require_auth),
):
    """List all resumes for the authenticated user."""
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.keycloak_id == user.get("keycloak_id"))
        )
        db_user = result.scalar_one_or_none()

        if not db_user:
            return ListResumesResponse(resumes=[], total=0)

        resumes_result = await db.execute(
            select(Resume)
            .where(Resume.user_id == db_user.id)
            .order_by(Resume.created_at.desc())
        )
        resumes = resumes_result.scalars().all()

        items = [
            ListResumeItem(
                id=str(r.id),
                filename=r.filename,
                status=ResumeStatus(r.status),
                job_title=r.job_title,
                created_at=r.created_at,
            )
            for r in resumes
        ]

    return ListResumesResponse(resumes=items, total=len(items))


@router.get("/{resume_id}", response_model=ResumeResult)
async def get_resume(
    resume_id: str,
    user: dict = Depends(require_auth),
):
    """Get resume details including OCR, ATS score, and improvements."""
    async with get_db() as db:
        result = await db.execute(
            select(Resume).where(Resume.id == resume_id)
        )
        resume = result.scalar_one_or_none()

        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")

        # Verify ownership
        user_result = await db.execute(
            select(User).where(User.keycloak_id == user.get("keycloak_id"))
        )
        db_user = user_result.scalar_one_or_none()
        if not db_user or resume.user_id != db_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        return ResumeResult(
            id=str(resume.id),
            user_id=str(resume.user_id),
            filename=resume.filename,
            ocr_json=resume.ocr_json or {},
            ats_score=resume.ats_score_json if resume.ats_score_json else None,
            improvements=resume.improvements_json if resume.improvements_json else None,
            status=ResumeStatus(resume.status),
            job_title=resume.job_title,
            experience_years=resume.experience_years,
            created_at=resume.created_at,
            updated_at=resume.updated_at,
        )


@router.post("/{resume_id}/regenerate")
async def regenerate_pipeline(
    resume_id: str,
    user: dict = Depends(require_auth),
):
    """Re-run the full pipeline: OCR → ATS Score → LLM Improvements.

    Each stage runs in its own worker thread with an individual timeout budget so a
    single hung external call (MinIO, OCR engine, or Ollama) cannot block the request
    forever. On any infrastructure failure (not a resume-quality issue) the stage is
    aborted, ``status`` transitions to ``failed``, and an ``error_message`` is persisted
    so the failure survives a restart. Resume-quality failures (e.g. no text found) are
    *not* infra errors — they yield an empty/low-quality result and the pipeline continues.
    """

    async with get_db() as db:
        result = await db.execute(select(Resume).where(Resume.id == resume_id))
        resume = result.scalar_one_or_none()

        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")

        # Verify ownership
        user_result = await db.execute(
            select(User).where(User.keycloak_id == user.get("keycloak_id"))
        )
        db_user = user_result.scalar_one_or_none()
        if not db_user or resume.user_id != db_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Mark the resume as processing up front so a crash mid-pipeline leaves it in
        # a recognizable (non-completed) state rather than stale "completed".
        resume.status = ResumeStatus.PROCESSING
        await db.commit()

        # ── Stage 1: OCR (infra — MinIO download + extraction) ─────────────
        try:
            ocr_json = await _run_stage(
                lambda: parse_text_to_json(
                    extract_text_from_file(
                        download_file(resume.minio_key), resume.file_type
                    )
                ),
                "OCR extraction",
            )
        except StageTimeout:
            await _pipeline_failure(db, resume, "OCR stage timed out")
        except Exception as e:  # infra failure (MinIO/parse), not resume quality
            logger.error(f"OCR stage failed: {e}")
            await _pipeline_failure(db, resume, f"OCR extraction error: {e}")

        # ── Stage 2: ATS scoring (pure/deterministic) ─────────────────────
        try:
            ats_score = await _run_stage(
                lambda: calculate_ats_score(ocr_json, resume.job_title),
                "ATS scoring",
            )
        except Exception as e:  # unexpected error in the scorer itself
            logger.error(f"ATS scoring stage failed: {e}")
            await _pipeline_failure(db, resume, f"ATS scoring error: {e}")

        # ── Stage 3: LLM improvements (infra — Ollama) with fallback ───────
        try:
            improvements = await _run_stage(
                lambda: generate_improvements(ocr_json, ats_score, resume.job_title),
                "LLM improvements",
            )
        except StageTimeout:
            # Ollama hung — persist a deterministic fallback so the user still gets value.
            logger.warning("LLM stage timed out; using deterministic fallback")
            improvements = _get_fallback_improvements(ats_score)
        except Exception as e:  # unexpected error wrapping generate_improvements()
            logger.error(f"LLM stage failed: {e}")
            await _pipeline_failure(db, resume, f"Improvement generation error: {e}")

        # Persist final results.
        resume.ocr_json = ocr_json or {}
        resume.ats_score_json = ats_score
        resume.improvements_json = improvements
        resume.status = ResumeStatus.COMPLETED
        await db.commit()

    return {
        "status": "completed",
        "resume_id": resume_id,
        "ats_score": ats_score,
        "improvements": improvements,
    }


async def _run_stage(fn: Callable[[], T], stage_name: str) -> T:
    """Run blocking ``fn`` in a worker thread, bounded by the per-stage timeout.

    The whole pipeline shares ``PIPELINE_TIMEOUT_SECONDS`` divided across stages, so a
    single stage can never monopolize the request. The blocking work runs on an event
    loop *executor*, and ``asyncio.wait_for`` enforces the timeout without parking the
    event loop — other requests keep being served while a stage is timing out.

    A thread cannot be forcibly killed in Python, so on timeout we best-effort cancel
    the pending work (it may run to completion in the background) and raise
    ``StageTimeout`` so the caller can persist a failure. Any other exception propagates
    to the caller, which decides whether it is infra-vs-resume-quality.
    """

    per_stage_budget = max(1, PIPELINE_TIMEOUT_SECONDS // 3)
    loop = asyncio.get_event_loop()
    future = loop.run_in_executor(None, fn)

    try:
        return await asyncio.wait_for(
            asyncio.shield(asyncio.wrap_future(future)), timeout=per_stage_budget
        )
    except (asyncio.TimeoutError, StageTimeout):
        future.cancel()  # best effort — a running thread cannot be forcibly killed
        raise StageTimeout(f"{stage_name} exceeded {per_stage_budget}s budget")


async def _pipeline_failure(
    db: Any, resume: "Resume", message: str
) -> NoReturn:
    """Persist ``status='failed'`` + ``error_message`` and return a 500 response."""

    try:
        resume.status = ResumeStatus.FAILED
        resume.error_message = message[:2000]  # guard against pathologically long text
        await db.commit()
    except Exception as e:  # pragma: no cover - defensive; logging is enough here
        logger.error(f"Failed to persist error state: {e}")

    raise HTTPException(status_code=500, detail=message)


@router.delete("/{resume_id}", response_model=DeleteResponse)
async def delete_resume(
    resume_id: str,
    user: dict = Depends(require_auth),
):
    """Delete a resume and its file."""
    async with get_db() as db:
        result = await db.execute(select(Resume).where(Resume.id == resume_id))
        resume = result.scalar_one_or_none()

        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")

        # Verify ownership
        user_result = await db.execute(
            select(User).where(User.keycloak_id == user.get("keycloak_id"))
        )
        db_user = user_result.scalar_one_or_none()
        if not db_user or resume.user_id != db_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Delete from MinIO
        try:
            delete_file(resume.minio_key)
        except Exception as e:
            logger.warning(f"MinIO delete warning: {e}")

        # Delete from database
        await db.delete(resume)
        await db.commit()

    return DeleteResponse(message="Resume deleted successfully", deleted=True)
