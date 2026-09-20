# Resume Platform — API Contracts

Authoritative endpoint contract shared between the FastAPI backend (`api/`) and
the Next.js WebUI (`webui/src/lib/api.ts`). Every endpoint, request/response
schema (from `api/models.py`), and error code is documented here.

Base path: `/api/v1`. Public keys come from `GET /config`; never leak secrets.

> Auth convention: every protected route requires a real Bearer token and
> enforces **ownership** (the resume's `user_id` must match the caller). Public
> routes are marked `[PUBLIC]`.

---

## 0. Health & Metadata

### `GET /health` — [PUBLIC]
- **200** → `{ "status": "healthy", "version": "<semver>", "timestamp": "<ISO-8601>" }`

### `GET /api/v1/internal/health` — [INTERNAL]
- Requires header `X-API-Key: <API_SECRET>` (shared secret, matches n8n API key).
- **403** if header missing/mismatched.
- **200** → same shape as `/health`.

---

## 1. Auth — `POST /api/v1/auth/*`

### `GET /config` — [PUBLIC]
Returns Keycloak connection info for the frontend (no secrets).

- **Response 200** → `{ "kcUrl": str, "realm": str, "clientId": str }`

### `POST /auth-url` — [PUBLIC]
Return a Keycloak hosted-flow URL.

- **Body**: `{ "action": str | null }` — `register` (default) or `forgotPassword`.
- **Response 200** → `{ "url": str }`

### `POST /exchange` — [PUBLIC]
Exchange a Keycloak authorization **code** for tokens (server-side, keeps the
confidential client secret out of the browser).

- **Body**: `{ "code": str, "redirect_uri": str | null }`
- **Response 200** → `{ "token": "<sub>", "user": { ... } }`
- **401** → `{ "error": "Authentication failed. Please try signing in again." }`

### `POST /verify` — [AUTH REQUIRED]
Verify a Bearer token and return user info.

- **Header**: `Authorization: Bearer <token>`
- **Response 200** → `{ "valid": true, "user": { ... } }`
- **401** → `Invalid authorization header` (missing/malformed) or `Invalid or expired token`.

### Local email/password flows (`/signup`, `/verify-otp`, `/forgot-password`, `/reset-password`)
These use a self-contained bcrypt credential store + short-lived 6-digit OTP.

### `POST /signup` — [PUBLIC]
Create a local account; OTP verification completes it. Never reveals whether the
email exists (generic response).

- **Body**: `{ "email": str, "password": str, "name": str | null }`
- **202** → `{ "status": "otp_sent", "email": "<lowercased>", "token": "<OTP JWT>" }`
- **400** → weak password (generic message).
- **409** → duplicate email.

### `POST /verify-otp` — [PUBLIC]
Complete signup OR validate a password-reset OTP.

- **Body**: `{ "token": "<OTP JWT>", "otp": str }`
- **200** → `{ "token": "<access>", "user": { ... } }` (signup) or a validation result.
- **401** → invalid/expired/wrong code.

### `POST /forgot-password` — [PUBLIC]
Issue a reset OTP for the given email (generic response).

- **Body**: `{ "email": str }`
- **202** → `{ "status": "otp_sent", "email": "<lowercased>", "token": "<OTP JWT>" }`

### `POST /reset-password` — [PUBLIC]
Set a new password after verifying the OTP.

- **Body**: `{ "token": "<OTP JWT>", "otp": str, "new_password": str }`
- **201** → `{ "token": "<access>", "user": { ... } }`
- **400/401** → invalid OTP or weak password.

### `POST /n8n/callback` — [INTERNAL]
Internal endpoint for n8n to push processing results.

- **Header**: `X-API-Key: <API_SECRET>`
- **403** if header missing/mismatched.

---

## 2. Resumes — `POST /api/v1/resume/*`

All routes are `[AUTH REQUIRED]` and enforce ownership. Auth runs **before**
validation (so a missing token returns 401, not 422).

### `POST /upload` — [AUTH REQUIRED]
Upload a resume for processing. A submission is identified by caller email +
filename; re-submitting returns **409** (never a duplicate record or 500).

- **Body**: multipart form — `file` (PDF/DOCX/JPG/PNG, ≤ 10 MB) + optional `job_title`, `experience_years`.
- **201** → `{ "resume_id": str, "status": "processing", "message": "Resume uploaded successfully. Processing started." }`
- **401** → missing/invalid Bearer token (auth runs first).
- **400** → unsupported file type. Allowed: `application/pdf`,
  `application/vnd.openxmlformats-officedocument.wordprocessingml.document`,
  `image/png`, `image/jpeg`, `image/jpg`.
- **413** → file exceeds MAX_FILE_SIZE (default 10 MB).
- **409** → duplicate application for this email+filename (checked before MinIO write;
  also caught via `IntegrityError` at insert for the race case).
- **500** → MinIO upload failure.

### `GET /` — [AUTH REQUIRED]
List all resumes for the caller (newest first).

- **200** → `{ "resumes": [ { "id", "filename", "status", "job_title", "created_at" } ], "total": int }`
- **200** with empty list if the caller has no user row.

### `GET /{resume_id}` — [AUTH REQUIRED]
Get details (OCR, ATS score, improvements).

- **200** → `{ "id", "user_id", "filename", "ocr_json": {}, "ats_score": {...}|null,
  "improvements": {...}|null, "status", "job_title", "experience_years",
  "created_at", "updated_at" }`
- **403** → resume exists but does not belong to caller.
- **404** → no such resume.

### `POST /{resume_id}/regenerate` — [AUTH REQUIRED]
Re-run the full pipeline: OCR → ATS Score → LLM Improvements.

- **200** → `{ "status": "completed", "resume_id": str, "ats_score": {...}, "improvements": {...} }`
- **403** → ownership mismatch.
- **404** → no such resume.
- **500** → MinIO download or OCR failure (logged).

### `DELETE /{resume_id}` — [AUTH REQUIRED]
Delete a resume and its MinIO object (delete-on-cascade).

- **200** → `{ "message": "Resume deleted successfully", "deleted": true }`
- **403** → ownership mismatch.
- **404** → no such resume.

---

## 3. Internal — `POST /api/v1/internal/*`
Gated by `X-API-Key`. Used exclusively by the n8n workflow engine.

### `POST /n8n/process-resume`
- **Body**: `{ "resume_id": str, "action": "score"|"improve", "data": {...} }`
- **200** → `{ "status": "ok", "resume_id": str, "action": str }`
- **400** → missing `resume_id`/`action`.
- **403** → bad API key.
- **404** → resume not found.

### `POST /n8n/ocr`
- **Body**: `{ "resume_id": str, "minio_key": str, "file_type": str }`
- **200** → `{ "resume_id", "ocr_json": {...}, "status": "ocr_completed" }`
- **400** → missing `resume_id`/`minio_key`.
- **500** → MinIO download or OCR failure.

---

## 4. Error-Code Summary

| Code | Meaning | Where |
|------|---------|-------|
| 201 | Created / signup-OTP sent / reset done | upload, local auth routes |
| 202 | OTP issued (signup / forgot-password) | `/auth/signup`, `/auth/forgot-password` |
| 400 | Bad request (type, missing field) | upload type check, auth validation |
| 401 | Unauthorized (bad/missing token) | all protected routes, `/auth/verify` |
| 403 | Forbidden (ownership / bad API key) | resume routes, internal endpoints |
| 404 | Not found | single-resume GET / DELETE / regenerate, n8n endpoints |
| 405 | Method not allowed | default FastAPI behavior |
| 409 | Duplicate application (idempotent) | upload race / pre-check |
| 413 | Payload too large (MAX_FILE_SIZE) | upload size check |
| 422 | Validation error (missing body field) | JSON-body routes without auth-first ordering |
| 500 | Server error (MinIO/OCR failure) | upload, regenerate, n8n/ocr |

---

## 5. Data Models (from `api/models.py`)

- **Enums**: `ResumeStatus` = pending | processing | completed | failed.
- **Request**: `UploadRequest(file_name, file_size, file_type, job_title?, experience_years?)`,
  `ATSFeedbackRequest(ocr_json, job_title?)`, `ImprovementRequest(ocr_json, ats_score, job_title?)`.
- **Response**: `ATSScore(overall, keywords_match, formatting, completeness, section_scores{}, missing_keywords[], recommendations[])`,
  `ResumeResult(id, user_id, filename, ocr_json{}, ats_score?, improvements?, status, job_title?, experience_years?, created_at, updated_at)`,
  `UploadResponse(resume_id, status, message)`, `ScoreResponse(ats_score)`,
  `ImprovementResponse(improvements)`, `ListResumesResponse(resumes[], total)`,
  `DeleteResponse(message, deleted)`.

---

## 6. Auth Flow (summary)

1. WebUI → `GET /config` + `POST /auth-url`.
2. Keycloak hosted flow (or local email/password) → authorization `code` or OTP JWT.
3. WebUI → `POST /exchange` (OIDC) to get a Bearer token; or verify OTP for local.
4. WebUI sends `Authorization: Bearer <token>` on every protected call; the server
   validates via auth-wrapper (preferred) → Keycloak introspection (fallback), with
   local login-JWT decoding when `AUTH_JWT_SECRET` is configured.
