# Resume Platform — Test Matrix

> **Generated:** 2026-08-25
> **Scope:** Full-stack — API (FastAPI/Python) + WebUI (Next.js/TypeScript)
> **Coverage:** Unit → Module → Integration → E2E

---

## 1. Feature Map & User Journeys

### 1.1 Features

| # | Feature | Module | Description |
|---|---------|--------|-------------|
| F1 | Landing Page | webui/src/app/page.tsx | Hero, how-it-works, features, CTA |
| F2 | Login / Keycloak OIDC | webui/src/app/login/, auth-context.tsx | Keycloak redirect + demo login |
| F3 | Signup | webui/src/app/signup/page.tsx | Keycloak redirect |
| F4 | Dashboard | webui/src/app/dashboard/page.tsx | List user's resumes with status |
| F5 | Resume Upload | webui/src/app/upload/page.tsx + routes/resumes.py | File upload (PDF/DOCX/JPG/PNG), job title, experience |
| F6 | Resume Detail | webui/src/app/resume/[id]/page.tsx | ATS score gauge, improvements, profile extraction |
| F7 | Templates | webui/src/app/templates/page.tsx | Browse resume templates |
| F8 | ATS Scoring | api/services/ats.py | Keyword match, formatting, completeness, quality |
| F9 | OCR Extraction | api/services/ocr.py | PDF (pypdf+tesseract), DOCX (python-docx), Image (Surya/tesseract) |
| F10 | LLM Improvements | api/services/llm.py | Ollama Qwen 0.5B → rewritten sections, suggestions |
| F11 | File Storage | api/services/minio.py | MinIO upload/download/delete |
| F12 | Auth (Keycloak) | api/services/auth.py | Token validation via auth-wrapper or Keycloak introspection |
| F13 | n8n Callbacks | api/routes/internal.py | Internal API for n8n OCR/score/improve callbacks |
| F14 | n8n Pipeline | n8n/workflows/resume-pipeline.json | Webhook → OCR → ATS → LLM → Save Results |
| F15 | Health Check | api/main.py + routes/internal.py | `/health` and `/api/v1/internal/health` |

### 1.2 User Journeys

| Journey | Steps | Pages/Endpoints |
|---------|-------|-----------------|
| J1: Guest Landing | Visit landing → Browse features → Click "Upload" | `/` → `/upload` |
| J2: Demo Mode | Visit landing → "Start with demo data" → Dashboard → View resume detail | `/` → `/dashboard` → `/resume/{id}` |
| J3: Auth Login | Visit login → Keycloak redirect → Callback → Dashboard | `/login` → Keycloak → `/auth/callback` → `/dashboard` |
| J4: Upload Resume | Login → Upload page → Select file + job title → Submit → Detail page | `/upload` → POST `/api/v1/resume/upload` → `/resume/{id}` |
| J5: Re-run Pipeline | Detail page → Click "Re-run" → Wait → Updated results | `/resume/{id}` → POST `/api/v1/resume/{id}/regenerate` |
| J6: Delete Resume | Detail page → Click "Delete" → Redirect to dashboard | `/resume/{id}` → DELETE `/api/v1/resume/{id}` → `/dashboard` |
| J7: Browse Templates | Visit templates → Click "Use this template" → Upload | `/templates` → `/upload` |

---

## 2. API Test Matrix (FastAPI / Python)

### 2.1 Unit Tests (No external dependencies)

| ID | Test | Module | What it validates |
|----|------|--------|-------------------|
| U01 | ATS score bounded 0-100 | services/ats.py | `calculate_ats_score()` always returns scores in [0,100] |
| U02 | Complete resume scores high | services/ats.py | Well-formed resume with all sections scores > sparse |
| U03 | No job title = neutral keywords | services/ats.py | `_calculate_keyword_match()` returns 50 when job_title is None |
| U04 | Keyword match reports missing | services/ats.py | Missing keywords list is populated correctly |
| U05 | Completeness scoring | services/ats.py | `_calculate_completeness()` counts present sections |
| U06 | Formatting scoring | services/ats.py | `_calculate_formatting()` penalizes no bullets, short text |
| U07 | Section quality scoring | services/ats.py | `_calculate_section_quality()` checks action verbs, quantification |
| U08 | Recommendations generation | services/ats.py | `_generate_recommendations()` produces actionable text |
| U09 | OCR parse detects sections | services/ocr.py | `parse_text_to_json()` identifies experience, skills, education |
| U10 | OCR parse falls back to raw | services/ocr.py | Text without headers → `raw_text` key |
| U11 | DOCX text extraction | services/ocr.py | `extract_text_from_docx()` extracts paragraphs |
| U12 | File type routing | services/ocr.py | `extract_text_from_file()` routes by MIME type |
| U13 | Image OCR returns string | services/ocr.py | `extract_text_from_image()` always returns str |
| U14 | LLM fallback structure | services/llm.py | `_get_fallback_improvements()` has all required keys |
| U15 | LLM fallback clamped score | services/llm.py | `estimated_ats_score_after` ≤ 100 |
| U16 | Pydantic model bounds | models.py | `ATSScore` rejects overall > 100 |
| U17 | ResumeStatus enum values | models.py | All enum values match expected strings |
| U18 | UploadResponse model | models.py | `UploadResponse` serializes correctly |
| U19 | LLM response parsing | services/llm.py | `_parse_llm_response()` handles markdown code blocks |
| U20 | LLM truncation | services/llm.py | `generate_improvements()` truncates resume content to 4000 chars |

### 2.2 Module Tests (Single service, mocked dependencies)

| ID | Test | Module | What it validates |
|----|------|--------|-------------------|
| M01 | Auth token validation success | services/auth.py | `validate_token()` returns user dict on 200 |
| M02 | Auth token validation failure | services/auth.py | `validate_token()` returns None on 401 |
| M03 | Auth fallback to Keycloak | services/auth.py | Falls back to Keycloak introspection when auth-wrapper fails |
| M04 | MinIO upload success | services/minio.py | `upload_file()` returns object key |
| M05 | MinIO upload failure | services/minio.py | `upload_file()` raises on S3Error |
| M06 | MinIO download success | services/minio.py | `download_file()` returns bytes |
| M07 | MinIO delete success | services/minio.py | `delete_file()` returns True |
| M08 | MinIO file exists | services/minio.py | `file_exists()` returns True/False |
| M09 | MinIO singleton pattern | services/minio.py | `get_minio_client()` returns same instance |
| M10 | OCR PDF extraction | services/ocr.py | `extract_text_from_pdf()` extracts text from text-layered PDF |
| M11 | OCR scanned PDF fallback | services/ocr.py | Scanned PDF → tesseract fallback |
| M12 | LLM Ollama connection failure | services/llm.py | ConnectionError → fallback improvements |
| M13 | LLM invalid JSON response | services/llm.py | Non-JSON response → fallback improvements |
| M14 | Auth wrapper URL config | services/auth.py | `get_auth_wrapper_url()` returns configured URL |

### 2.3 Integration Tests (API routes with TestClient, mocked services)

| ID | Test | Route | What it validates |
|----|------|-------|-------------------|
| I01 | Route registration smoke | main.py | All expected routes registered |
| I02 | Health check returns 200 | GET /health | Returns status, version, timestamp |
| I03 | Internal health check | GET /api/v1/internal/health | Returns healthy status |
| I04 | Auth verify success | POST /api/v1/auth/verify | Returns valid=True with user info |
| I05 | Auth verify invalid token | POST /api/v1/auth/verify | Returns 401 |
| I06 | Auth verify missing header | POST /api/v1/auth/verify | Returns 422 (missing Authorization) |
| I07 | Upload with valid file | POST /api/v1/resume/upload | Returns resume_id, status=processing |
| I08 | Upload file too large | POST /api/v1/resume/upload | Returns 413 |
| I09 | Upload unsupported type | POST /api/v1/resume/upload | Returns 400 |
| I10 | Upload no file | POST /api/v1/resume/upload | Returns 422 |
| I11 | Upload without auth | POST /api/v1/resume/upload | Returns 401 |
| I12 | List resumes | GET /api/v1/resume/ | Returns list with total |
| I13 | List empty | GET /api/v1/resume/ | Returns empty list, total=0 |
| I14 | Get resume detail | GET /api/v1/resume/{id} | Returns full resume with OCR, score, improvements |
| I15 | Get resume not found | GET /api/v1/resume/{id} | Returns 404 |
| I16 | Get resume access denied | GET /api/v1/resume/{id} | Returns 403 (wrong user) |
| I17 | Regenerate pipeline | POST /api/v1/resume/{id}/regenerate | Returns completed with score + improvements |
| I18 | Regenerate not found | POST /api/v1/resume/{id}/regenerate | Returns 404 |
| I19 | Delete resume | DELETE /api/v1/resume/{id} | Returns deleted=True |
| I20 | Delete not found | DELETE /api/v1/resume/{id} | Returns 404 |
| I21 | Delete access denied | DELETE /api/v1/resume/{id} | Returns 403 |
| I22 | n8n callback score | POST /api/v1/auth/n8n/callback | Updates ATS score, status=completed |
| I23 | n8n callback improve | POST /api/v1/auth/n8n/callback | Updates improvements, status=completed |
| I24 | n8n callback wrong key | POST /api/v1/auth/n8n/callback | Returns 403 |
| I25 | n8n callback missing data | POST /api/v1/auth/n8n/callback | Returns 400 |
| I26 | n8n process-resume | POST /api/v1/internal/n8n/process-resume | Updates resume with score/improvements |
| I27 | n8n OCR endpoint | POST /api/v1/internal/n8n/ocr | Returns structured ocr_json |
| I28 | n8n OCR wrong key | POST /api/v1/internal/n8n/ocr | Returns 403 |
| I29 | n8n OCR missing minio_key | POST /api/v1/internal/n8n/ocr | Returns 400 |
| I30 | n8n OCR download failure | POST /api/v1/internal/n8n/ocr | Returns 500 |

### 2.4 End-to-End Tests (Full pipeline, real OCR)

| ID | Test | What it validates |
|----|------|-------------------|
| E01 | Scanned PDF OCR E2E | Real tesseract OCR on scanned PDF → structured sections → ATS score |
| E02 | Text-layered PDF | pypdf extracts text without OCR → parse → score |
| E03 | DOCX full pipeline | DOCX upload → text extraction → parse → ATS score |
| E04 | n8n workflow E2E | Node simulation of full pipeline: Webhook → OCR → ATS → LLM → Save |
| E05 | Workflow structure | n8n JSON has correct nodes, types, connections, settings |
| E06 | Workflow OCR node | OCR node calls internal endpoint via fetch (not stub) |
| E07 | Workflow LLM node | LLM node uses fetch, not axios |
| E08 | Workflow save node | Save node calls process-resume endpoint with API key |

---

## 3. WebUI Test Matrix (Next.js / TypeScript)

### 3.1 Unit Tests (Component-level, React Testing Library)

| ID | Test | Component | What it validates |
|----|------|-----------|-------------------|
| UI01 | Landing page renders | page.tsx | H1, CTA buttons, feature cards present |
| UI02 | Landing CTA links | page.tsx | "Upload" links to /upload, "Templates" links to /templates |
| UI03 | Login page renders | login/page.tsx | Keycloak login button, demo login button |
| UI04 | Signup page renders | signup/page.tsx | Keycloak signup redirect |
| UI05 | Dashboard renders | dashboard/page.tsx | "My Resumes" heading, upload button |
| UI06 | Dashboard empty state | dashboard/page.tsx | Empty inbox icon, "Upload your first resume" button |
| UI07 | Dashboard loading state | dashboard/page.tsx | "Loading resumes…" text |
| UI08 | Resume card renders | resume-card.tsx | Filename, job title, status badge, ATS score |
| UI09 | Resume card links | resume-card.tsx | "Review" links to /resume/{id} |
| UI10 | Upload page renders | upload/page.tsx | Dropzone, job title input, experience input, submit button |
| UI11 | Upload file validation | upload-dropzone.tsx | Rejects unsupported file types |
| UI12 | Upload file size validation | upload-dropzone.tsx | Rejects files > 10MB |
| UI13 | Upload submit flow | upload-dropzone.tsx | Calls api.upload, redirects on success |
| UI14 | Upload error display | upload-dropzone.tsx | Shows error message |
| UI15 | Resume detail renders | resume/[id]/page.tsx | Filename, status badge, action buttons |
| UI16 | ATS gauge renders | ats-score.tsx | Score number, color coding (green ≥70, amber ≥50, red <50) |
| UI17 | ATS gauge score clamping | ats-score.tsx | Score clamped to 0-100 range |
| UI18 | Improvements list renders | improvements-list.tsx | Rewritten sections, suggestions, keyword suggestions |
| UI19 | Status badge colors | status-badge.tsx | Correct color per status (completed=green, processing=amber, etc.) |
| UI20 | Templates page renders | templates/page.tsx | 6 template cards, each with "Use this template" button |
| UI21 | Auth context loginDemo | auth-context.tsx | Sets token and user in localStorage |
| UI22 | Auth context logout | auth-context.tsx | Clears token and user, redirects to /login |
| UI23 | Auth context persistence | auth-context.tsx | Restores token/user from localStorage on mount |
| UI24 | API client verify | api.ts | Sends Bearer token, parses response |
| UI25 | API client list | api.ts | Fetches /resume/, returns resumes array |
| UI26 | API client upload | api.ts | Sends FormData with file, returns resume_id |
| UI27 | API client regenerate | api.ts | POST /resume/{id}/regenerate |
| UI28 | API client remove | api.ts | DELETE /resume/{id} |
| UI29 | API client timeout | api.ts | Aborts after 8 seconds |
| UI30 | Demo fixtures structure | demo.ts | demoResumes has 5 items, demoDetail returns valid data |

### 3.2 Module Tests (Hook-level, mocked API)

| ID | Test | Hook | What it validates |
|----|------|------|-------------------|
| UM01 | useList with token | use-data.ts | Calls api.list, sets data |
| UM02 | useList without token | use-data.ts | Returns empty list |
| UM03 | useList API failure | use-data.ts | Falls back to demoResumes |
| UM04 | useDetail with token | use-data.ts | Calls api.get, sets data |
| UM05 | useDetail without token | use-data.ts | Returns demoDetail |
| UM06 | useDetail API failure | use-data.ts | Falls back to demoDetail |
| UM07 | useDetail touch refresh | use-data.ts | touch() re-triggers fetch |

### 3.3 Integration Tests (Page-level, mocked API)

| ID | Test | Page | What it validates |
|----|------|------|-------------------|
| II01 | Landing → Upload navigation | / → /upload | Click "Upload your resume" navigates to upload |
| II02 | Landing → Templates navigation | / → /templates | Click "Browse templates" navigates to templates |
| II03 | Landing → Dashboard (demo) | / → /dashboard | Click "Start with demo data" → login demo → dashboard |
| II04 | Dashboard → Resume detail | /dashboard → /resume/{id} | Click "Review" on a resume card |
| II05 | Resume detail → Dashboard | /resume/{id} → /dashboard | Click "Back to my resumes" |
| II06 | Resume detail → Re-run | /resume/{id} | Click "Re-run" → action message → data refresh |
| II07 | Resume detail → Delete | /resume/{id} → /dashboard | Click "Delete" → redirect to dashboard |
| II08 | Templates → Upload | /templates → /upload | Click "Use this template" on any card |
| II09 | Upload → Resume detail | /upload → /resume/{id} | Upload with demo token → redirect to detail |
| II10 | Auth callback flow | /auth/callback | Keycloak callback sets credentials |

### 3.4 End-to-End Tests (Full browser, Playwright)

| ID | Test | What it validates |
|----|------|-------------------|
| EE01 | Full guest journey | Landing → Browse → Upload → (redirect to login) |
| EE02 | Full demo journey | Landing → Demo login → Dashboard → View resume → Re-run → Delete |
| EE03 | Upload flow | Login → Upload page → Select file → Submit → Detail page with results |
| EE04 | Templates browse | Templates page → Click template → Upload page |
| EE05 | ATS score visualization | Detail page → Gauge shows correct score → Color coding correct |
| EE06 | Improvements display | Detail page → Rewritten sections visible → Suggestions list |
| EE07 | Status badge colors | Dashboard → Each resume shows correct status color |
| EE08 | Responsive layout | View pages at mobile (375px), tablet (768px), desktop (1280px) widths |
| EE09 | Navigation consistency | All pages have navbar, footer |
| EE10 | Error handling | Upload with no file → error message shown |

---

## 4. Test Execution Summary

| Category | Count | Framework |
|----------|-------|-----------|
| API Unit Tests | 20 | pytest |
| API Module Tests | 14 | pytest |
| API Integration Tests | 30 | pytest + TestClient |
| API E2E Tests | 8 | pytest + real tesseract |
| UI Unit Tests | 30 | Vitest + React Testing Library |
| UI Module Tests | 7 | Vitest + React Testing Library |
| UI Integration Tests | 10 | Vitest + React Testing Library |
| UI E2E Tests | 10 | Playwright |
| **Total** | **129** | |

---

## 5. Bug Tracker (Post-Test)

Bugs identified during testing will be tracked in the `BUGS.md` file with:
- Bug ID (BUG-NNN)
- Severity (P0-P3)
- Module affected
- Steps to reproduce
- Expected vs actual behavior
- Fix status
