# Resume Platform Architecture

**Date:** 2026-08-25
**Product:** resume.iacgenie.com
**Pattern:** OCR → Deterministic ATS → LLM Improvements

## Architecture

```
Internet → Cloudflare → Nginx → Docker Compose
                              ├── resume-api (FastAPI, :3006)
                              ├── n8n (workflow, :3005)
                              └── Ollama (Qwen 0.5B, :11434)
                              ↓
                         Shared: PostgreSQL, Redis, MinIO, Keycloak
```

## Services

### Resume API (FastAPI)
- **Port:** 3006
- **Stack:** Python 3.11, FastAPI, SQLAlchemy async, Pydantic v2
- **Endpoints:**
  - `POST /api/v1/resume/upload` — Upload resume (PDF/DOCX/JPG)
  - `GET /api/v1/resume/` — List user resumes
  - `GET /api/v1/resume/{id}` — Get resume with results
  - `POST /api/v1/resume/{id}/regenerate` — Re-run full pipeline
  - `DELETE /api/v1/resume/{id}` — Delete resume
  - `POST /api/v1/auth/verify` — Verify token
  - `POST /api/v1/internal/n8n/process-resume` — n8n callback
  - `GET /health` — Health check

### n8n Workflow
- **Port:** 3005
- **Workflow:** resume-pipeline.json
- **Pipeline:** Webhook → Extract → OCR → ATS Score → LLM → Save
- **Deterministic:** ATS scoring in code node (no LLM)
- **LLM:** Qwen 0.5B via Ollama for improvement generation

### OCR Service
- **Primary:** Surya OCR (CPU-based, supports 100+ languages)
- **Fallback:** pypdf for text-based PDFs
- **DOCX:** python-docx
- **Output:** Structured JSON with sections, raw_text, word_count

### ATS Scoring Engine
- **Fully deterministic** — no LLM involved
- **4 dimensions:**
  - Keywords match (30%): Industry-specific keyword matching
  - Formatting (25%): Bullet points, spacing, word count
  - Completeness (30%): Required sections present
  - Section quality (15%): Action verbs, quantification, dates
- **Output:** Overall score (0-100), per-section scores, missing keywords, recommendations

### LLM Service
- **Model:** Qwen 2.5 0.5B via Ollama
- **Prompt:** Resume content + ATS score + job title → improvements JSON
- **Fallback:** Deterministic suggestions when Ollama unavailable
- **Output:** rewritten_sections, suggestions, keyword_suggestions, formatting_tips

## Database Schema

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    keycloak_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size INTEGER NOT NULL,
    minio_key VARCHAR(500) NOT NULL,
    ocr_json JSONB,
    ats_score_json JSONB,
    improvements_json JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    job_title VARCHAR(255),
    experience_years INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## Resource Budget

| Service | RAM | CPU | Disk |
|---------|-----|-----|------|
| Resume API | 512 MB | 0.5 core | Minimal |
| n8n | 1 GB | 1.0 core | ~500 MB |
| **Total New** | **~1.5 GB** | **~1.5 cores** | **~500 MB** |

## File Structure

```
resume-platform/
├── ARCHITECTURE.md
├── docker-compose.resume-platform.yml
├── nginx/resume-platform.conf
├── api/
│   ├── main.py
│   ├── models.py
│   ├── database.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── services/
│   │   ├── ocr.py
│   │   ├── ats.py
│   │   ├── llm.py
│   │   ├── minio.py
│   │   └── auth.py
│   └── routes/
│       ├── auth.py
│       ├── resumes.py
│       └── internal.py
└── n8n/
    └── workflows/resume-pipeline.json
```
