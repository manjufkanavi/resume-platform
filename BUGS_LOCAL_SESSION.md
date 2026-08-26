# Resume Platform — Local E2E Testing & Bug-Fix Summary

**Date:** 2026-08-26
**Role:** Senior Test Engineer
**Goal:** Establish a runnable local instance exercising the *real* application code (all FastAPI routes + real OCR + real ATS engine + real LLM-improvement with Ollama fallback) against lightweight local storage + stubbed auth, then drive the full demo journey end-to-end in the browser, root-causing and fixing anything broken — especially the backend integration and the **review → suggestion → remedy** flow.

## How to run locally

```bash
# Backend (real app, SQLite + in-MinIO + stub auth + Ollama->LLM fallback) on :3006
cd ~/.hermes/git_clone_dir/resume-platform/api
LOCAL_DEV=1 python local_server.py

# WebUI (Next.js) on :3007, proxies /api/* -> 127.0.0.1:3006
cd ~/.hermes/git_clone_dir/resume-platform/webui
npm run dev        # or: NEXT_PUBLIC_API_URL=http://127.0.0.1:3006 npx next dev -p 3007
```

Browse: http://127.0.0.1:3007/  (landing) → "Start with demo data" → dashboard → resume detail.

## Bugs found & fixed (this session)

### Backend (critical — pipeline integration)
1. **`require_auth` read the token as a *query* param, not the `Authorization` header.** Fixed to use FastAPI `Header(default="Bearer ")`. This single bug broke the entire authenticated pipeline (upload/list/get/regenerate/delete → 401).
2. **`n8n/callback` returned 500.** Fixed: removed an erroneous `from main import get_db` (duplicate/incorrect import).
3. **`get_db()` missing `@asynccontextmanager`.** Added it — every DB-touching endpoint was broken.
4. **`gen_random_uuid()` (PostgreSQL) on SQLite.** Registered a SQLite function via a `sync_engine` `connect` event listener so the production model column works on SQLite.

### WebUI (this session — E2E blockers)
5. **Detail page `ResumePage` was an *async* Client Component.** `export default async function ResumePage({ params }) { await params }` + `"use client"` → Next.js 16 suspends indefinitely (page renders empty). **Fixed:** read the route param synchronously via `useParams()`; the component is now a synchronous client wrapper that delegates to `ResumeDetailClient`.
6. **`Re-run` deadlock.** The button was `disabled={data.status === "processing"}`, but upload sets `status=processing` and nothing transitions it — so the pipeline could never be triggered via the UI (button stuck disabled, resume stuck "processing"). **Fixed:** `disabled={data.status === "processing" && !!(data.ats_score || data.improvements)}` — allow triggering the pipeline when a processing resume has no results yet.

## N8n callback fix (latent, verified)
`n8n/callback` now returns 200 (was 500). Requires a valid `X-API-Key` header to be meaningful.

## End-to-end verification (browser)

Full journey driven in the browser against the **real** backend (no app stubbing — only storage/auth lightened):

1. **Upload** a real DOCX (`alex_chen_so_engineering.docx`) via the UI → redirect to `/resume/{id}` (status `processing`).
2. **Click Re-run** → pipeline runs (OCR → ATS scoring → LLM-improvement with Ollama fallback) → **"Done — results updated."**.
3. **Detail page** shows the real results:
   - **ATS Score: 47** (overall), section breakdown (Keyword 50 / Formatting 65 / Completeness 20), per-section scores.
   - **Recommendations**: "Add missing sections…", "Expand your resume…".
   - **AI-written summary** (the *remedy*): "Add a 2-3 line professional summary…".
   - **Suggested improvements** (the *suggestions*): "Add missing sections…".

The **review → suggestion → remedy flow works end-to-end** against the real backend.

Screenshot: `~/.hermes/cache/screenshots/browser_screenshot_19b36326c6114d3c9aad04c90e4c6d4c.png`

## Regression: pytest
Baseline **65 tests** (64 passed, 1 skipped) — **all still pass** after the fixes. Only pre-existing `on_event` deprecation warnings remain.

## Environment notes / limitations
- No Docker / Postgres / MinIO / Keycloak / Ollama / n8n available → production stack cannot stand up.
- Local mode uses: in-memory SQLite (aiosqlite), in-MinIO byte store, stubbed auth, Ollama that fast-fails to the deterministic LLM fallback.
- Scanned PDFs/images OCR returns `""` (tesseract/Surya not installed); LLM uses `_get_fallback_improvements` (real rewrite logic, no live model).
- In-MinIO store is per-process: a resume created by one API process can't be re-run by another after restart (minio_key points to an in-memory object that's gone). Keep a single API process running for consistent state.
