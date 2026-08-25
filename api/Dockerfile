FROM python:3.11-slim

WORKDIR /app

# Minimal system deps (no Surya for now - use pypdf only)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 3006

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:3006/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3006", "--workers", "2"]
