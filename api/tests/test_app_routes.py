"""Route-registration smoke test.

Verifies the FastAPI app wires up every endpoint required by Phase 1 tasks
1.1 (structure), 1.3 (auth), 1.4 (upload), 1.6 (internal/n8n) without needing
live Postgres/MinIO/Keycloak/Ollama — importing the app only registers routes;
the startup DB `create_all` does NOT run on import.
"""
import inspect

from main import app


EXPECTED_STATIC_ROUTES = [
    "/health",
    "/api/v1/auth/verify",
    "/api/v1/auth/n8n/callback",
    "/api/v1/resume/upload",
    "/api/v1/resume/",
    "/api/v1/resume/{resume_id}",
    "/api/v1/resume/{resume_id}/regenerate",
    "/api/v1/internal/n8n/process-resume",
    "/api/v1/internal/health",
]


def _registered_paths():
    return {r.path for r in app.routes if hasattr(r, "path")}


def test_all_expected_routes_registered():
    registered = _registered_paths()
    missing = [r for r in EXPECTED_STATIC_ROUTES if r not in registered]
    assert not missing, f"Routes missing from app: {missing}"


def test_app_metadata_and_health_route_present():
    assert app.title == "Resume Platform API"
    paths = _registered_paths()
    assert "/health" in paths


def test_route_count_reasonable():
    # ~11 declared routes; allow slack for OpenAPI/docs routes.
    assert 9 <= len(_registered_paths()) <= 40


def test_upload_endpoint_declares_file_and_form_params():
    from fastapi import UploadFile, Form

    upload_route = next(
        (r for r in app.routes
         if getattr(r, "path", "") == "/api/v1/resume/upload"),
        None,
    )
    assert upload_route is not None, "upload route not registered"
    # The POST handler should declare File(...) + Form(...) params.
    params = inspect.signature(upload_route.endpoint).parameters
    assert "file" in params and "job_title" in params
