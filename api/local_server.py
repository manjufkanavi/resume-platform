"""Local development server for the resume platform.

Stands up the REAL FastAPI application (all routes + real OCR + real ATS engine +
real LLM-improvement code with Ollama fallback) against lightweight in-process
substitutes for the production external services, so the full resume pipeline can
be exercised end-to-end in a browser without Postgres / MinIO / Keycloak / Ollama:

  * Database  -> SQLite (aiosqlite) via guarded column-type shims.
                 Production behaviour (DATABASE_URL unset) is byte-for-byte
                 unchanged. Local mode is enabled only with LOCAL_DEV=1.
  * MinIO     -> in-memory byte store (upload / download / delete).
  * Auth      -> stubbed: any non-empty "Bearer <token>" maps to a fixed local
                 user (bypasses Keycloak / auth-wrapper).
  * Ollama    -> points at localhost:11434 so the connection fails fast and the
                 deterministic LLM fallback produces the review/suggestions.

Run:   LOCAL_DEV=1 python local_server.py      (serves on 127.0.0.1:3006)
"""

from __future__ import annotations

import json
import os
import sys
import uuid as _uuid_lib

_API_DIR = os.path.dirname(os.path.abspath(__file__))
if _API_DIR not in sys.path:
    sys.path.insert(0, _API_DIR)

# ── Environment: enable local mode + point at local substitutes ─────────────
os.environ["LOCAL_DEV"] = "1"
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./local_resume.db")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "local-dev")
os.environ.setdefault("MINIO_SECRET_KEY", "local-dev-secret")
os.environ.setdefault("API_SECRET", "change-me-secret")
os.environ.setdefault("OLLAMA_URL", "http://127.0.0.1:11434")
os.environ.setdefault("OLLAMA_MODEL", "qwen2.5:0.5b")
os.environ.setdefault(
    "ALLOWED_ORIGINS",
    "http://127.0.0.1:3007,http://localhost:3007,http://127.0.0.1:3000,http://localhost:3000",
)

# ── 1. Make the PostgreSQL model columns work on SQLite (guarded) ────────────
from sqlalchemy import JSON as _JSON, String as _String, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB, UUID as _PGUUID

import database  # noqa: E402  (must import after env is set)


class _SQLiteUUID(TypeDecorator):
    """Store UUIDs as TEXT(36) on SQLite; behave like UUID elsewhere."""

    impl = _String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return str(value) if value is not None else None

    def process_result_value(self, value, dialect):
        return str(value) if value is not None else None


class _SQLiteJSON(TypeDecorator):
    """Store JSONB as TEXT on SQLite."""

    impl = _JSON
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value) if isinstance(value, str) else value


for _model in (database.User, database.Resume):
    for _col in _model.__table__.columns:
        if isinstance(_col.type, _PGUUID):
            _col.type = _SQLiteUUID()
        elif isinstance(_col.type, JSONB):
            _col.type = _SQLiteJSON()

# ── Provide PostgreSQL gen_random_uuid() on local SQLite ─────────────────────
from sqlalchemy import event as _sqla_event  # noqa: E402


@_sqla_event.listens_for(database.engine.sync_engine, "connect")
def _register_gen_random_uuid(dbapi_connection, connection_record):
    """Emulate PostgreSQL's gen_random_uuid() for local SQLite (pre-3.44)."""
    try:
        dbapi_connection.create_function(
            "gen_random_uuid", 0, lambda: str(_uuid_lib.uuid4())
        )
    except Exception:
        pass

# ── 2. In-memory MinIO substitute ────────────────────────────────────────────
import services.minio as _minio  # noqa: E402
from minio.error import S3Error  # noqa: E402

_MINIO_STORE: dict[str, bytes] = {}


def _upload_file(file_bytes: bytes, filename: str, content_type: str) -> str:
    key = f"resumes/{filename}"
    _MINIO_STORE[key] = bytes(file_bytes)
    return key


def _download_file(object_key: str) -> bytes:
    if object_key not in _MINIO_STORE:
        raise S3Error("NoSuchKey", code="404", message="object not found")
    return _MINIO_STORE[object_key]


def _delete_file(object_key: str) -> bool:
    _MINIO_STORE.pop(object_key, None)
    return True


_minio.upload_file = _upload_file
_minio.download_file = _download_file
_minio.delete_file = _delete_file

# ── 3. Stubbed auth (any non-empty Bearer token -> fixed local user) ─────────
import services.auth as _auth  # noqa: E402


async def _get_user_from_token(token: str) -> dict | None:
    if not token:
        return None
    return {
        "keycloak_id": "local-dev-user",
        "email": "local@resume.dev",
        "name": "Local Dev",
    }


_auth.get_user_from_token = _get_user_from_token

# ── 4. Build the real app (routers pick up the patched dependencies) ─────────
from main import app  # noqa: E402


def main() -> None:
    import uvicorn

    print(
        "[local_server] serving real app on http://127.0.0.1:3006 "
        "(SQLite + in-memory MinIO + stub auth + LLM fallback)",
        flush=True,
    )
    uvicorn.run(app, host="127.0.0.1", port=3006, log_level="info")


if __name__ == "__main__":
    main()
