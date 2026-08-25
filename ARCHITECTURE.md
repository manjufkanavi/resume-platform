# Resume Platform — System Architecture

**Domain:** `resume.iacgenie.com`
**Owner:** Manjunath Kanavi (manjufkanavi)
**Date:** 2026-08-25
**Status:** Design Phase

---

## 1. Executive Summary

AI-powered resume review platform providing:
- **Resume Upload & OCR Extraction** — PDF/DOCX/JPG → structured JSON
- **ATS Score Analysis** — keyword matching, formatting, completeness scoring
- **Resume Improvement** — LLM-generated suggestions and rewritten content
- **User Authentication** — Keycloak OIDC via existing auth-wrapper

Deployed on existing IacGenie home server (192.168.0.118) with shared infrastructure.

---

## 2. Infrastructure Context

### 2.1 Host Server
| Resource | Value |
|----------|-------|
| CPU | 8 cores |
| RAM | 15 GB (9.5 GB free) |
| OS | Ubuntu (newvm) |
| Docker | Compose (iacgenie project) |

### 2.2 Existing Services (Port Map)
| Service | Port | Container |
|---------|------|-----------|
| Keycloak (auth) | 9003 | iacgenie_keycloak |
| SearXNG | 8082 | iacgenie_searxng |
| LightSerp API | 8000 | iacgenie_lightserp_api |
| LightSerp WebUI | 3001 | iacgenie_lightserp_webui |
| Gitea | 3000 | iacgenie_gitea |
| OpenBao | 8200 | iacgenie_openbao |
| Grafana | 3004 | iacgenie_grafana |
| Prometheus | 9090 | iacgenie_prometheus |
| Auth Wrapper | 9096 | iacgenie_auth_wrapper |
| CrowdSec | 3033 | iacgenie_crowdsec |
| Loki | 3100 | iacgenie_loki |
| Postgres | 5432 | iacgenie_postgres |
| PgBouncer | 6432 | iacgenie_pgbouncer |
| Redis | 6379 | iacgenie_redis |
| NSQD | 4150 | iacgenie_nsqd |
| IacGenie Frontend | 3002 | iacgenie_frontend |
| IacGenie Backend | 3003 | iacgenie_backend |

### 2.3 Available Ports
| Port | Service |
|------|---------|
| **3005** | n8n (workflow engine) |
| **3006** | Resume API (FastAPI) |
| **3007** | Surya OCR (optional, or use CPU) |

### 2.4 Existing Infrastructure to Reuse
- **Nginx** — reverse proxy at `/home/mkanavi/docker/iacgenie/nginx/`
- **Cloudflare Tunnel** — DNS + HTTPS termination
- **Keycloak** — OIDC authentication (realm: `iacgenie`)
- **Auth Wrapper** — OIDC proxy middleware
- **PostgreSQL** — shared database (iacgenie_postgres)
- **Redis** — shared cache/queue (iacgenie_redis)
- **MinIO** — shared object storage (iacgenie_minio)
- **OpenBao** — secrets management (iacgenie_openbao)
- **Ollama** — already installed (3.74GB image) for local LLM serving

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Internet                                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                   Cloudflare Tunnel                              │
│                   (iacgenie-tunnel)                              │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                     Nginx (iacgenie-nginx)                       │
│                                                                  │
│  resume.iacgenie.com → proxy_pass http://127.0.0.1:3006         │
│                                                                  │
│  Security Headers: HSTS, CSP, X-Frame-Options, etc.             │
│  Rate Limiting: general zone (10r/s), auth zone (3r/m)          │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│              resume-platform Docker Compose                      │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────────────┐  │
│  │  Resume     │  │    n8n      │  │   Surya OCR (optional) │  │
│  │  API        │→ │  (workflow  │  │   (or Tesseract)       │  │
│  │  FastAPI    │  │   engine)   │  │                        │  │
│  │  :3006      │  │  :3005      │  │                        │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬─────────────┘  │
│         │                 │                     │                │
│         │                 ▼                     │                │
│         │          ┌─────────────┐              │                │
│         │          │  Ollama     │              │                │
│         │          │  :11434     │              │                │
│         │          │  (Qwen2.5   │              │                │
│         │          │   0.5B)     │              │                │
│         │          └─────────────┘              │                │
│         │                                       │                │
│  ┌──────▼──────┐  ┌─────────────┐  ┌───────────▼─────────────┐  │
│  │  PostgreSQL │  │    Redis    │  │      MinIO               │  │
│  │  (shared)   │  │  (shared)   │  │  (shared, resume files) │  │
│  │  :5432      │  │  :6379      │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. Service Details

### 4.1 Resume API (FastAPI) — Port 3006

**Purpose:** REST API for resume upload, processing status, results retrieval

**Tech Stack:**
- Python 3.11 + FastAPI
- SQLAlchemy + Alembic (PostgreSQL ORM)
- Pydantic v2 (request/response models)
- MinIO SDK (file storage)
- Keycloak OIDC integration (via auth-wrapper)

**Endpoints:**

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/auth/login` | Keycloak OAuth2 flow redirect | Public |
| POST | `/api/v1/resume/upload` | Upload resume file (PDF/DOCX/JPG) | Required |
| GET | `/api/v1/resume/{id}` | Get resume details + OCR JSON | Required |
| GET | `/api/v1/resume/{id}/score` | Get ATS score | Required |
| GET | `/api/v1/resume/{id}/improvements` | Get LLM improvement suggestions | Required |
| POST | `/api/v1/resume/{id}/regenerate` | Re-run full pipeline | Required |
| GET | `/api/v1/resume/` | List user's resumes | Required |
| DELETE | `/api/v1/resume/{id}` | Delete resume | Required |

**Data Models:**

```python
class ResumeUpload(BaseModel):
    file: UploadFile
    job_title: str | None = None  # optional target job title
    experience_years: int | None = None

class ATSScore(BaseModel):
    overall: int              # 0-100
    keywords_match: int       # 0-100
    formatting: int           # 0-100
    completeness: int         # 0-100
    section_scores: dict      # {section: score}
    missing_keywords: list[str]
    recommendations: list[str]

class ResumeImprovement(BaseModel):
    rewritten_sections: dict  # {section: new_text}
    suggestions: list[str]
    keyword_suggestions: list[str]
    formatting_tips: list[str]
    ats_score_after: int | None

class ResumeResult(BaseModel):
    id: str
    user_id: str
    filename: str
    ocr_json: dict            # extracted content
    ats_score: ATSScore | None
    improvements: ResumeImprovement | None
    status: str               # pending | processing | completed | failed
    created_at: datetime
    updated_at: datetime
```

**Database Schema (PostgreSQL):**

```sql
-- Users table (mirrors Keycloak for local session tracking)
CREATE TABLE users (
    id UUID PRIMARY KEY,
    keycloak_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Resumes table
CREATE TABLE resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    minio_key VARCHAR(500) NOT NULL,  -- MinIO object key
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(10) NOT NULL,   -- pdf, docx, jpg, png
    job_title VARCHAR(255),
    experience_years INTEGER,
    ocr_json JSONB,                    -- extracted content from OCR
    ats_score JSONB,                   -- ATS analysis result
    improvements JSONB,                -- LLM improvement suggestions
    status VARCHAR(20) DEFAULT 'pending', -- pending, processing, completed, failed
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Processing queue (Redis-backed, but tracked in DB)
CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id UUID REFERENCES resumes(id) ON DELETE CASCADE,
    n8n_webhook_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'queued', -- queued, running, completed, failed
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_resumes_user ON resumes(user_id);
CREATE INDEX idx_resumes_status ON resumes(status);
CREATE INDEX idx_processing_resume ON processing_jobs(resume_id);
```

### 4.2 n8n Workflow Engine — Port 3005

**Purpose:** Deterministic workflow orchestration for resume processing pipeline

**Tech Stack:**
- n8n (self-hosted, Docker)
- n8n Community Nodes

**Workflow: Resume Processing Pipeline**

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  HTTP Webhook│     │  Surya OCR  │     │  JSON Parse │
│  (trigger)  │────▶│  (extract)  │────▶│  & Validate │
│             │     │             │     │             │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌─────────────┐             │
                    │  Save OCR   │◀────────────┘
                    │  to MinIO   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐     ┌─────────────┐
                    │  ATS Score  │────▶│  Keyword     │
                    │  Engine     │     │  Extraction  │
                    └──────┬──────┘     └──────┬──────┘
                           │                   │
                    ┌──────▼──────┐     ┌──────▼──────┐
                    │  Section    │     │  Format     │
                    │  Analysis   │     │  Validation │
                    └──────┬──────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │  Combine    │
                    │  ATS Score  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐     ┌─────────────┐
                    │  LLM Judge  │────▶│  Qwen2.5-   │
                    │  (Qwen 0.5B)│     │  0.5B-Instruct│
                    │  (Ollama)   │     │  via API    │
                    └──────┬──────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │  Generate   │
                    │  Improvements│
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Update     │
                    │  Resume DB  │
                    │  (PostgreSQL)│
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Notify     │
                    │  API (webhook)│
                    └─────────────┘
```

**n8n Workflow Nodes:**

1. **HTTP Webhook** — receives upload event from Resume API
   - Payload: `{resume_id, user_id, minio_key, job_title, file_type}`

2. **Surya OCR** — extract text from resume
   - Input: MinIO presigned URL
   - Output: structured JSON with sections, text, layout

3. **JSON Parse & Validate** — validate OCR output
   - Check required fields: name, experience, skills, education
   - Flag missing sections

4. **ATS Score Engine** — deterministic scoring
   - **Keyword Match (40% weight):**
     - Extract keywords from job_title (or use default tech keywords)
     - TF-IDF matching against resume text
     - Score = (matched_keywords / total_keywords) × 100
   - **Formatting (30% weight):**
     - Check for proper section headers
     - Check for bullet points
     - Check for contact info
     - Check for date formats
   - **Completeness (30% weight):**
     - Required sections: contact, experience, education, skills
     - Score = (present_sections / required_sections) × 100

5. **LLM Judge (Qwen2.5-0.5B)** — resume analysis & improvement
   - Input: OCR JSON + ATS score + job_title
   - Prompt template (see §5.3)
   - Output: rewritten sections, suggestions, keyword recommendations

6. **Save Results** — update PostgreSQL
   - Upsert ats_score and improvements into resumes table

7. **Notify API** — webhook back to Resume API
   - Signal processing complete

### 4.3 Surya OCR (Optional) — CPU-based

**Purpose:** Extract structured text from resume files

**Tech Stack:**
- Surya (Python library, runs on CPU)
- Or Tesseract OCR as fallback

**Supported Formats:**
- PDF (multi-page)
- DOCX
- JPG/PNG (scanned resumes)

**Output Format:**

```json
{
  "metadata": {
    "page_count": 1,
    "language": "en",
    "confidence": 0.95
  },
  "sections": [
    {
      "type": "contact",
      "title": "Contact Information",
      "content": "John Doe\njohn@example.com\n(555) 123-4567\nlinkedin.com/in/johndoe",
      "fields": {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "(555) 123-4567",
        "linkedin": "linkedin.com/in/johndoe"
      }
    },
    {
      "type": "experience",
      "title": "Work Experience",
      "content": "Senior Software Engineer at Google (2020-Present)\n- Led team of 5 engineers...\n- Reduced latency by 40%...",
      "entries": [
        {
          "company": "Google",
          "title": "Senior Software Engineer",
          "period": "2020-Present",
          "achievements": ["Led team of 5 engineers", "Reduced latency by 40%"]
        }
      ]
    },
    {
      "type": "education",
      "title": "Education",
      "content": "MS Computer Science, Stanford University (2018-2020)\nBS Computer Science, MIT (2014-2018)",
      "entries": [
        {
          "degree": "MS Computer Science",
          "institution": "Stanford University",
          "period": "2018-2020"
        }
      ]
    },
    {
      "type": "skills",
      "title": "Skills",
      "content": "Python, JavaScript, React, Node.js, Docker, Kubernetes, AWS, PostgreSQL",
      "skills": ["Python", "JavaScript", "React", "Node.js", "Docker", "Kubernetes", "AWS", "PostgreSQL"]
    }
  ]
}
```

### 4.4 Ollama + Qwen2.5-0.5B

**Purpose:** Local LLM for resume analysis and improvement generation

**Model:** `qwen2.5:0.5b` (or `qwen3:0.6b` if available)

**Deployment:**
- Ollama already installed on server (3.74GB image)
- Pull model: `ollama pull qwen2.5:0.5b`
- API endpoint: `http://127.0.0.1:11434/api/generate`
- Runs on CPU (~2-5 seconds per response)

**Resource Usage:**
- RAM: ~1 GB (0.5B model, quantized)
- CPU: 1-2 cores during inference
- Disk: ~1 GB model weight

---

## 5. Detailed Design

### 5.1 Authentication Flow

```
User → resume.iacgenie.com → Nginx → Auth Wrapper (9096) → Keycloak (9003)
                                                    │
                                                    ▼
                                            OIDC Token (JWT)
                                                    │
                                                    ▼
                                            Resume API (3006)
                                            - Validates JWT
                                            - Extracts user_id
                                            - Serves protected endpoints
```

**Keycloak Client Configuration:**
- Client ID: `resume-platform`
- Client Type: `confidential`
- Redirect URI: `https://resume.iacgenie.com/api/v1/auth/callback`
- Valid URIs: `https://resume.iacgenie.com/*`
- Secret: stored in OpenBao (`secret/resume-platform/client-secret`)

**Auth Wrapper Configuration:**
- Add `RESUME_PLATFORM_CLIENT_ID` and `RESUME_PLATFORM_CLIENT_SECRET`
- Map Keycloak roles to resume-platform roles

### 5.2 File Storage Flow

```
User uploads resume → Resume API → MinIO (iacgenie_minio)
                                    │
                                    ▼
                            Bucket: resume-files/
                            Key: {user_id}/{resume_id}/{filename}
                                    │
                                    ▼
                            n8n reads from MinIO
                            (presigned URL via API)
```

**MinIO Bucket Structure:**
```
resume-files/
├── {user_id}/
│   ├── {resume_id_1}/
│   │   ├── original.pdf
│   │   ├── ocr_output.json
│   │   └── improved_resume.pdf
│   └── {resume_id_2}/
│       └── ...
```

### 5.3 LLM Prompt Templates

**ATS Judge Prompt:**

```
You are an expert ATS (Applicant Tracking System) resume reviewer.
Analyze the following resume and provide a detailed ATS score.

Resume Content (JSON):
{ocr_json}

Target Job Title: {job_title}

Required sections for a strong resume:
1. Contact Information (name, email, phone, LinkedIn)
2. Professional Summary
3. Work Experience (with achievements, not just duties)
4. Education
5. Skills (technical and soft)
6. Certifications (if applicable)

Scoring Criteria:
- Keyword Match (40%): How well does the resume match keywords for "{job_title}"?
- Formatting (30%): Is the resume ATS-friendly? (proper headings, bullet points, no tables/graphics)
- Completeness (30%): Are all required sections present and substantive?

Return JSON:
{
  "overall_score": <0-100>,
  "keyword_match": <0-100>,
  "formatting": <0-100>,
  "completeness": <0-100>,
  "missing_keywords": ["keyword1", "keyword2"],
  "missing_sections": ["section1"],
  "recommendations": ["recommendation1", "recommendation2"]
}
```

**Resume Improvement Prompt:**

```
You are an expert resume writer and career coach.
Improve the following resume based on the ATS analysis.

Original Resume (JSON):
{ocr_json}

ATS Score: {ats_score}

Target Job Title: {job_title}

ATS Recommendations:
{ats_recommendations}

Instructions:
1. Rewrite weak sections with stronger, achievement-oriented language
2. Add missing keywords naturally
3. Improve formatting suggestions
4. Suggest additional skills/certifications relevant to "{job_title}"
5. Keep the tone professional and concise

Return JSON:
{
  "rewritten_sections": {
    "experience": "Improved experience section text...",
    "summary": "Improved summary text...",
    "skills": "Improved skills list..."
  },
  "suggestions": ["Add quantifiable metrics to experience", "Include more action verbs"],
  "keyword_suggestions": ["machine learning", "cloud computing", "agile"],
  "formatting_tips": ["Use consistent date format", "Add a professional summary"],
  "estimated_ats_score_after": <0-100>
}
```

### 5.4 ATS Scoring Algorithm (Deterministic)

```python
def calculate_ats_score(ocr_json: dict, job_title: str) -> dict:
    """
    Deterministic ATS scoring algorithm.
    No LLM involved — purely rule-based.
    """
    text = extract_all_text(ocr_json)
    sections = get_section_types(ocr_json)
    
    # 1. Keyword Match (40% weight)
    job_keywords = extract_keywords_from_job_title(job_title)
    # Use a curated keyword database per job family
    # e.g., "Software Engineer" → ["python", "java", "javascript", "sql", 
    #         "git", "docker", "aws", "api", "testing", "agile"]
    matched = count_keyword_matches(text, job_keywords)
    keyword_score = (matched / len(job_keywords)) * 100 if job_keywords else 50
    
    # 2. Formatting (30% weight)
    format_score = 0
    if has_bullet_points(text): format_score += 25
    if has_proper_headings(text): format_score += 25
    if has_contact_info(ocr_json): format_score += 25
    if has_date_format(text): format_score += 25
    # Penalize: tables, graphics, unusual fonts, columns
    if has_tables(text): format_score -= 20
    if has_columns(text): format_score -= 15
    
    # 3. Completeness (30% weight)
    required_sections = ["contact", "experience", "education", "skills"]
    present = sum(1 for s in required_sections if s in sections)
    completeness_score = (present / len(required_sections)) * 100
    
    # Weighted overall
    overall = (keyword_score * 0.4) + (format_score * 0.3) + (completeness_score * 0.3)
    
    return {
        "overall": round(overall),
        "keyword_match": round(keyword_score),
        "formatting": round(format_score),
        "completeness": round(completeness_score),
        "missing_keywords": [kw for kw in job_keywords if kw not in text.lower()],
        "recommendations": generate_recommendations(keyword_score, format_score, completeness_score)
    }
```

**Keyword Database (excerpt):**

| Job Family | Keywords |
|------------|----------|
| Software Engineer | python, java, javascript, typescript, sql, git, docker, kubernetes, aws, api, testing, agile, ci/cd, linux |
| Data Scientist | python, r, machine learning, deep learning, tensorflow, pytorch, sql, pandas, numpy, statistics, visualization |
| DevOps Engineer | docker, kubernetes, ansible, terraform, aws, gcp, azure, jenkins, ci/cd, monitoring, linux, networking |
| Product Manager | agile, scrum, roadmap, user stories, analytics, a/b testing, stakeholder management, jira, sql, ux |
| UX Designer | figma, sketch, user research, wireframing, prototyping, usability testing, html, css, design systems, accessibility |

### 5.5 n8n Workflow Definition (JSON)

```json
{
  "name": "Resume Processing Pipeline",
  "nodes": [
    {
      "id": "webhook-trigger",
      "name": "HTTP Webhook",
      "type": "n8n-nodes-base.webhook",
      "parameters": {
        "httpMethod": "POST",
        "path": "resume-process",
        "responseMode": "responseNode",
        "authentication": "headerAuth",
        "nodeAuthType": "headerAuth"
      }
    },
    {
      "id": "get-minio-url",
      "name": "Get MinIO Presigned URL",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://127.0.0.1:3006/api/v1/internal/minio-presign",
        "authentication": "genericCredentialType",
        "body": "={{ $json.minio_key }}"
      }
    },
    {
      "id": "surya-ocr",
      "name": "Surya OCR",
      "type": "n8n-nodes-base.executeWorkflow",
      "parameters": {
        "workflowId": "surya-ocr-workflow",
        "url": "={{ $json.presigned_url }}"
      }
    },
    {
      "id": "ats-score",
      "name": "ATS Score Engine",
      "type": "n8n-nodes-base.code",
      "parameters": {
        "functionCode": "// Deterministic scoring (see §5.4)"
      }
    },
    {
      "id": "llm-judge",
      "name": "LLM Judge (Qwen)",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://127.0.0.1:11434/api/generate",
        "body": {
          "model": "qwen2.5:0.5b",
          "prompt": "={{ $json.llm_prompt }}",
          "stream": false,
          "options": {
            "temperature": 0.3,
            "max_tokens": 2048
          }
        }
      }
    },
    {
      "id": "save-results",
      "name": "Save to PostgreSQL",
      "type": "n8n-nodes-base.postgres",
      "parameters": {
        "operation": "update",
        "table": "resumes",
        "columns": "ats_score,improvements,status,updated_at",
        "whereColumn": "id",
        "whereValue": "={{ $json.resume_id }}"
      }
    },
    {
      "id": "notify-api",
      "name": "Notify Resume API",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://127.0.0.1:3006/api/v1/internal/process-complete",
        "body": {
          "resume_id": "={{ $json.resume_id }}",
          "status": "completed"
        }
      }
    }
  ],
  "connections": {
    "webhook-trigger": {
      "main": [[{"node": "get-minio-url", "type": "main", "index": 0}]]
    },
    "get-minio-url": {
      "main": [[{"node": "surya-ocr", "type": "main", "index": 0}]]
    },
    "surya-ocr": {
      "main": [[{"node": "ats-score", "type": "main", "index": 0}]]
    },
    "ats-score": {
      "main": [[{"node": "llm-judge", "type": "main", "index": 0}]]
    },
    "llm-judge": {
      "main": [[{"node": "save-results", "type": "main", "index": 0}]]
    },
    "save-results": {
      "main": [[{"node": "notify-api", "type": "main", "index": 0}]]
    }
  }
}
```

---

## 6. Docker Compose Configuration

```yaml
# docker-compose.resume-platform.yml
# Place in: ~/docker/iacgenie/
# Deploy: docker compose -f docker-compose.resume-platform.yml up -d

version: "3.8"

services:
  # =====================
  # Resume API (FastAPI)
  # =====================
  resume-api:
    image: python:3.11-slim
    container_name: iacgenie_resume_api
    restart: unless-stopped
    ports:
      - "127.0.0.1:3006:8000"
    volumes:
      - ./resume-platform/api:/app
      - ./resume-platform/requirements.txt:/app/requirements.txt
    environment:
      - DATABASE_URL=postgresql://lightsrp:${PG_ROOT_PASSWORD}@iacgenie_postgres:5432/lightsrp
      - REDIS_URL=redis://iacgenie_redis:6379/1
      - MINIO_ENDPOINT=iacgenie_minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
      - KEYCLOAK_URL=http://iacgenie_keycloak:8080
      - KEYCLOAK_REALM=iacgenie
      - KEYCLOAK_CLIENT_ID=resume-platform
      - KEYCLOAK_CLIENT_SECRET=${RESUME_PLATFORM_CLIENT_SECRET}
      - AUTH_WRAPPER_URL=http://127.0.0.1:9096
      - N8N_URL=http://iacgenie_n8n:5678
      - OLLAMA_URL=http://127.0.0.1:11434
      - RESUME_BUCKET=resume-files
    depends_on:
      - n8n
    networks:
      - iacgenie-backend
    deploy:
      resources:
        limits:
          memory: "512m"
          cpus: "0.5"
    healthcheck:
      test: ["CMD-SHELL", "exec 6<>/dev/tcp/127.0.0.1:8000 && exec 6>&-"]
      interval: 30s
      timeout: 10s
      retries: 3
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "3"

  # =====================
  # n8n Workflow Engine
  # =====================
  n8n:
    image: docker.n8n.io/n8nio/n8n:latest
    container_name: iacgenie_n8n
    restart: unless-stopped
    ports:
      - "127.0.0.1:3005:5678"
    environment:
      - N8N_HOST=0.0.0.0
      - N8N_PORT=5678
      - N8N_PROTOCOL=https
      - N8N_SECURE_COOKIE=false
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=iacgenie_postgres
      - DB_POSTGRESDB_DATABASE=lightsrp
      - DB_POSTGRESDB_USER=lightsrp
      - DB_POSTGRESDB_PASSWORD=${PG_ROOT_PASSWORD}
      - DB_POSTGRESDB_PORT=5432
      - EXECUTIONS_MODE=queue
      - QUEUE_BULL_REDIS_HOST=iacgenie_redis
      - QUEUE_BULL_REDIS_PORT=6379
      - OLLAMA_URL=http://127.0.0.1:11434
      - MINIO_ENDPOINT=iacgenie_minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
    volumes:
      - ./n8n/data:/home/node/.n8n
    depends_on:
      - resume-api
    networks:
      - iacgenie-backend
    deploy:
      resources:
        limits:
          memory: "1g"
          cpus: "1.0"
    healthcheck:
      test: ["CMD-SHELL", "exec 6<>/dev/tcp/127.0.0.1:5678 && exec 6>&-"]
      interval: 30s
      timeout: 10s
      retries: 3
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "3"

networks:
  iacgenie-backend:
    external: true
    name: iacgenie_iacgenie-backend
```

---

## 7. Nginx vHost Configuration

Add to `/home/mkanavi/docker/iacgenie/nginx/conf.d/iacgenie.conf`:

```nginx
# Resume Platform
server {
    listen 443 ssl;
    http2 on;
    server_name resume.iacgenie.com;

    ssl_certificate /etc/letsencrypt/live/iacgenie.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/iacgenie.com/privkey.pem;

    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers on;

    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self';" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()" always;

    # Auth endpoint (redirect to Keycloak)
    location /api/v1/auth/ {
        limit_req zone=auth burst=3 nodelay;
        proxy_pass http://127.0.0.1:3006;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Internal API (no auth-wrapper, direct to API)
    location /api/v1/internal/ {
        proxy_pass http://127.0.0.1:3006;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Main API (through auth-wrapper)
    location /api/v1/ {
        proxy_pass http://127.0.0.1:9096;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Auth-User $remote_user;
    }

    # Frontend (if SPA)
    location / {
        proxy_pass http://127.0.0.1:3006;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 8. Cloudflare Tunnel Configuration

Add to Cloudflare Tunnel ingress rules:

| Rule | Service | Host | Path |
|------|---------|------|------|
| 1 | Resume API | resume.iacgenie.com | /* | → 127.0.0.1:3006 |

---

## 9. Resource Allocation Summary

| Service | RAM Limit | CPU Limit | Disk |
|---------|-----------|-----------|------|
| Resume API | 512 MB | 0.5 core | Minimal |
| n8n | 1 GB | 1.0 core | ~500 MB |
| Ollama (Qwen 0.5B) | 1 GB | 1-2 cores | ~1 GB (shared) |
| **Total New** | **~2.5 GB** | **~2.5 cores** | **~2 GB** |

**Available after deployment:**
- RAM: ~7 GB free
- CPU: ~5.5 cores free
- Disk: Plenty (existing data dirs)

---

## 10. Deployment Steps

### Phase 1: Infrastructure Setup
1. [ ] Pull Ollama model: `ollama pull qwen2.5:0.5b`
2. [ ] Create MinIO bucket: `resume-files/`
3. [ ] Create Keycloak client: `resume-platform`
4. [ ] Store secrets in OpenBao: `secret/resume-platform/`
5. [ ] Add n8n to docker-compose.yml
6. [ ] Add Resume API to docker-compose.yml
7. [ ] Add nginx vHost for resume.iacgenie.com
8. [ ] Add Cloudflare tunnel rule

### Phase 2: Application Development
1. [ ] Build Resume API (FastAPI)
2. [ ] Build n8n workflow (Resume Processing Pipeline)
3. [ ] Build Surya OCR integration
4. [ ] Build ATS scoring engine
5. [ ] Build LLM prompt templates
6. [ ] Build frontend (React/Next.js or simple HTML)

### Phase 3: Testing & Launch
1. [ ] Test upload → OCR → scoring → improvement pipeline
2. [ ] Load test with 100 concurrent uploads
3. [ ] Verify auth flow end-to-end
4. [ ] Deploy to production
5. [ ] Monitor for 48 hours

---

## 11. Security Considerations

| Concern | Mitigation |
|---------|-----------|
| File upload | Max 10MB, type validation, virus scan (ClamAV) |
| Auth | Keycloak OIDC via auth-wrapper |
| API | JWT validation, rate limiting |
| Data at rest | MinIO encryption, PostgreSQL encryption |
| Data in transit | HTTPS (Cloudflare + Let's Encrypt) |
| LLM output | Content filtering, output validation |
| PII | Resume data encrypted at rest, auto-delete after 90 days |

---

## 12. Future Enhancements

1. **Multi-language support** — Surya OCR supports 100+ languages
2. **Cover letter analysis** — extend pipeline to cover letters
3. **Job description matching** — upload JD + resume for match score
4. **Interview prep** — generate interview questions based on resume
5. **Resume templates** — generate ATS-optimized resume from JSON
6. **Analytics dashboard** — Grafana dashboard for usage metrics
7. **Batch processing** — upload multiple resumes at once
8. **Email notifications** — notify users when processing completes

---

## 13. File Structure

```
resume-platform/
├── ARCHITECTURE.md              # This file
├── docker-compose.resume-platform.yml
├── nginx/
│   └── resume-platform.conf     # Nginx vHost snippet
├── api/
│   ├── main.py                  # FastAPI application
│   ├── models.py                # Pydantic models
│   ├── database.py              # SQLAlchemy setup
│   ├── auth.py                  # Keycloak OIDC integration
│   ├── routes/
│   │   ├── auth.py              # Auth endpoints
│   │   ├── resumes.py           # Resume CRUD
│   │   └── internal.py          # Internal API (n8n → API)
│   ├── services/
│   │   ├── ocr.py               # Surya OCR integration
│   │   ├── ats.py               # ATS scoring engine
│   │   ├── llm.py               # Ollama/Qwen integration
│   │   └── minio.py             # MinIO file storage
│   └── requirements.txt
├── n8n/
│   └── workflows/
│       └── resume-pipeline.json # n8n workflow definition
├── frontend/                    # Optional: React/Next.js frontend
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   └── styles/
│   └── package.json
└── scripts/
    ├── setup-minio-bucket.sh
    ├── setup-keycloak-client.sh
    └── deploy.sh
```

---

## 14. Decision Log

| Decision | Option A | Option B | Choice | Rationale |
|----------|----------|----------|--------|-----------|
| OCR Engine | Surya | Tesseract | **Surya** | Better document understanding, structured output |
| LLM | Qwen2.5-0.5B | Qwen3-0.6B | **Qwen2.5-0.5B** | Available on Ollama, sufficient for resume analysis |
| Workflow Engine | n8n | Custom Python | **n8n** | Visual workflow, deterministic, easy to modify |
| Auth | Keycloak OIDC | JWT + Password | **Keycloak OIDC** | Already running, consistent with other services |
| Database | Shared Postgres | Separate Postgres | **Shared Postgres** | Resource constraints, single-VM |
| File Storage | MinIO | Local filesystem | **MinIO** | Already running, scalable |
| Frontend | React SPA | Static HTML | **React SPA** (Phase 2) | Better UX, but static HTML for MVP |
| Deployment | Docker Compose | Ansible role | **Docker Compose** (Phase 1) → Ansible (Phase 2) | Fast start, migrate to Ansible later |

---

*Document version: 1.0*
*Last updated: 2026-08-25*
