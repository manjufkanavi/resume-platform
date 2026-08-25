# Phase 0: Infrastructure Setup — COMPLETE ✅

**Date:** 2026-08-25
**Status:** All 7 sub-tasks completed

## Completed Tasks

### 0.1 ✅ Pull Ollama model (Qwen2.5-0.5B)
- Model `qwen2.5:0.5b` (397 MB) already pulled on remote server
- Accessible at `http://ollama:11434` (internal Docker network)

### 0.2 ✅ Create MinIO bucket (resume-files)
- Bucket `resume-files` created in MinIO
- Credentials: `iacgenie-minio` / `o9c1gFkhRYy1Wkz3P1aASLjXJ#215365TsdUsVdl`
- Accessible at `http://minio:9000` (internal Docker network)

### 0.3 ✅ Create Keycloak client (resume-platform)
- Client ID: `resume-platform`
- Client Secret: `gSvLDrhV1sQHvB9iLG6iYsvDzj74FEXh`
- Redirect URIs: `https://resume.iacgenie.com/*`
- Web Origins: `https://resume.iacgenie.com`
- Standard flow + direct access grants enabled

### 0.4 ✅ Store secrets in OpenBao
- New KV v2 engine: `resume-platform-kv`
- Secrets stored:
  - `MINIO_ACCESS_KEY`
  - `MINIO_SECRET_KEY`
  - `KEYCLOAK_CLIENT_ID`
  - `KEYCLOAK_CLIENT_SECRET`
  - `KEYCLOAK_URL`
  - `RESUME_API_SECRET`
  - `N8N_ENCRYPTION_KEY`

### 0.5 ✅ Add n8n + resume-api to docker-compose
- Added `n8n` service (port 3005)
- Added `resume-api` service (port 3006)
- Both services on `iacgenie-backend` network
- Health checks configured for both services

### 0.6 ✅ Add nginx vHost for resume.iacgenie.com
- Config: `/home/mkanavi/docker/iacgenie/nginx/conf.d/resume-platform.conf`
- Routes:
  - `/api/*` → resume-api (port 3006)
  - `/n8n/*` → n8n (port 3005)
  - `/` → resume-api (port 3006)
- Nginx restarted successfully

### 0.7 ✅ Add Cloudflare tunnel rule
- Cloudflare tunnel already has catch-all `*.iacgenie.com` rule
- No additional tunnel rule needed
- **Action Required:** Create DNS record for `resume.iacgenie.com` in Cloudflare dashboard

## Infrastructure Status

| Service | Status | Port |
|---------|--------|------|
| Ollama | ✅ Running | 11434 |
| MinIO | ✅ Healthy | 9000/9001 |
| Keycloak | ✅ Healthy | 8083 |
| OpenBao | ✅ Unsealed | 8200 |
| PostgreSQL | ✅ Healthy | 5432 |
| Redis | ✅ Healthy | 6379 |
| Nginx | ✅ Restarted | 443 |

## Next Steps

- **Phase 1:** Resume API Development (FastAPI)
- **Phase 2:** n8n Workflow Development
- **Phase 3:** Frontend Development
- **Phase 4:** Testing & Deployment

## Notes

- Fixed pre-existing infrastructure issues:
  - OpenBao was sealed → unsealed with 2 of 3 keys
  - MinIO was restarting → fixed credentials in .env file
  - Keycloak was restarting → added missing KC_DB_PASSWORD to .env file
- The `.env` file was updated with secrets from OpenBao
- All services are now running on the remote server (192.168.0.118)
