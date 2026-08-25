"""Tests for the n8n Resume Processing Pipeline workflow JSON.

Validates structure (nodes, types, connections) and that the two previously
stub/weak nodes are now real:
  - OCR Extraction -> calls the resume-api internal OCR endpoint via fetch.
  - LLM Improvements -> uses built-in fetch (not the unavailable axios).
  - Save Results -> calls the resume-api internal process-resume endpoint.
"""
import json
import os
import re

import pytest

WORKFLOW_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "n8n", "workflows", "resume-pipeline.json",
)

EXPECTED_NODES = [
    "Webhook Trigger",
    "Extract Data",
    "OCR Extraction",
    "ATS Scoring",
    "LLM Improvements",
    "Save Results",
]


@pytest.fixture()
def workflow():
    with open(WORKFLOW_PATH) as f:
        return json.load(f)


def test_workflow_name_and_node_count(workflow):
    assert workflow["name"] == "Resume Processing Pipeline"
    assert len(workflow["nodes"]) == len(EXPECTED_NODES)
    assert [n["name"] for n in workflow["nodes"]] == EXPECTED_NODES


def test_node_types(workflow):
    types = {n["name"]: n["type"] for n in workflow["nodes"]}
    # Only the trigger is a base node; the rest are Code nodes.
    assert types["Webhook Trigger"] == "n8n-nodes-base.webhook"
    for name in EXPECTED_NODES[1:]:
        assert types[name] == "n8n-nodes-base.code"


def test_connections_form_linear_chain(workflow):
    connections = workflow["connections"]
    order = EXPECTED_NODES
    for i in range(len(order) - 1):
        nxt = connections[order[i]]["main"][0][0]
        assert nxt["node"] == order[i + 1], (
            f"{order[i]} should connect to {order[i + 1]}"
        )


def test_webhook_trigger_registers_upload_path(workflow):
    trigger = next(n for n in workflow["nodes"] if n["name"] == "Webhook Trigger")
    assert trigger["parameters"]["path"] == "resume-upload"
    assert trigger["parameters"]["httpMethod"] == "POST"


def test_ocr_node_calls_internal_endpoint(workflow):
    node = next(n for n in workflow["nodes"] if n["name"] == "OCR Extraction")
    code = node["parameters"]["code"]
    # Real fetch call to the internal OCR endpoint (not a stub).
    assert "fetch(" in code
    assert "http://resume-api:3006/api/v1/internal/n8n/ocr" in code
    # It must flatten ocr_json downstream so the ATS node can read .sections.
    assert "ocr_json" in code


def test_llm_node_uses_fetch_not_axios(workflow):
    node = next(n for n in workflow["nodes"] if n["name"] == "LLM Improvements")
    code = node["parameters"]["code"]
    assert "await fetch(" in code
    assert "http://ollama:11434/api/generate" in code
    # axios is NOT bundled in n8n code nodes — must not be used as a call.
    assert not re.search(r"axios\.\w+", code), "LLM node still calls axios()"


def test_save_results_node_calls_internal_api(workflow):
    node = next(n for n in workflow["nodes"] if n["name"] == "Save Results")
    code = node["parameters"]["code"]
    assert "http://resume-api:3006/api/v1/internal/n8n/process-resume" in code
    assert "X-API-Key" in code


def test_workflow_has_queue_execution_settings(workflow):
    assert workflow.get("settings", {}).get("executionTimeout", 0) > 0
