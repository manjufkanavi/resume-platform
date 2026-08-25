"""End-to-end test of the n8n workflow (Phase 2.7).

Executes the *actual* n8n Code-node JavaScript in connection order using Node,
with `fetch` mocked to simulate the external services (OCR API, Ollama,
resume-api). This drives the full pipeline Webhook -> Extract -> OCR -> ATS ->
LLM -> Save and asserts a populated, structured result.
"""
import json
import os
import subprocess
import tempfile

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WF = os.path.join(REPO, "n8n", "workflows", "resume-pipeline.json")

# The Node simulation: topologically orders Code nodes from the workflow
# connections, then runs each node's code with a mock $input and a mocked
# global fetch that returns canned responses for the external services.
NODE_SCRIPT = r"""
const fs = require('fs');
const wf = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const nodes = wf.nodes;
const byName = {};
nodes.forEach(n => byName[n.name] = n);

// Build incoming-edge map to compute execution order.
const incoming = {};
nodes.forEach(n => incoming[n.name] = []);
Object.keys(wf.connections).forEach(src => {
  (wf.connections[src].main || []).forEach(arr =>
    arr.forEach(({ node }) => incoming[node].push(src)));
});

// Topological order starting from trigger(s) with no incoming edges.
const order = [];
const visited = new Set();
let queue = nodes.filter(n => (incoming[n.name] || []).length === 0).map(n => n.name);
while (queue.length) {
  const name = queue.shift();
  if (visited.has(name)) continue;
  visited.add(name);
  order.push(byName[name]);
  const outs = (wf.connections[name] && wf.connections[name].main)
    ? wf.connections[name].main[0] : [];
  outs.forEach(({ node }) => { if (!visited.has(node)) queue.push(node); });
}

// Mock fetch for the three external services so the pipeline runs offline.
global.fetch = async (url, opts) => {
  const body = opts && opts.body ? JSON.parse(opts.body) : {};
  if (url.includes('/api/v1/internal/n8n/ocr')) {
    const ocrJson = {
      sections: {
        experience: 'Built microservices achieving 90% latency reduction. Led a team of engineers.',
        skills: 'Python, Docker, Kubernetes, AWS',
        education: 'BS Computer Science',
        summary: 'Senior software engineer with 6 years experience'
      },
      raw_text: 'Senior software engineer. Built microservices. Led a team.',
      word_count: 240,
      line_count: 5
    };
    return { ok: true, status: 200, json: async () => ({ ocr_json: ocrJson }) };
  }
  if (url.includes('/api/generate')) {
    const respObj = {
      rewritten_sections: { experience: 'Quantified impact: reduced latency by 90%.' },
      suggestions: ['Quantify more achievements with numbers.'],
      keyword_suggestions: ['kubernetes', 'terraform'],
      formatting_tips: ['Use consistent bullet points.'],
      estimated_ats_score_after: 88
    };
    return { ok: true, status: 200, json: async () => ({ response: JSON.stringify(respObj) }) };
  }
  if (url.includes('/n8n/process-resume')) {
    return { ok: true, status: 200, json: async () => ({ status: 'ok' }) };
  }
  return { ok: true, status: 200, json: async () => ({}) };
};

function makeInput(data) { return { first: () => ({ json: data }) }; }

async function runNode(code, data) {
  const fn = new Function('$input', '$json', 'process', 'console', 'fetch',
    `return (async () => { ${code} })()`);
  const result = await fn(makeInput(data), data, process, console, global.fetch);
  return (result && result[0] && result[0].json) ? result[0].json : data;
}

let data = {
  resume_id: 'resume-e2e-1', filename: 'resume.pdf',
  file_type: 'application/pdf', file_size: 12345,
  job_title: 'software engineer', experience_years: 6,
  minio_key: 'resumes/resume-e2e-1.pdf', status: 'processing'
};

(async () => {
  for (const node of order) {
    if (node.type !== 'n8n-nodes-base.code') continue;
    data = await runNode(node.parameters.code, data);
  }
  process.stdout.write(JSON.stringify(data, null, 2));
})();
"""


def test_workflow_executes_end_to_end():
    fd, script = tempfile.mkstemp(suffix=".cjs")
    with os.fdopen(fd, "w") as f:
        f.write(NODE_SCRIPT)
    try:
        r = subprocess.run(
            ["node", script, WF], capture_output=True, text=True, timeout=60
        )
        assert r.returncode == 0, f"node simulation failed: {r.stderr}"
        final = json.loads(r.stdout)
    finally:
        if os.path.exists(script):
            os.remove(script)

    # Full pipeline produced a structured, populated result.
    assert final["resume_id"] == "resume-e2e-1"
    assert final["status"] == "pipeline_complete"

    # ATS/LLM scoring ran through the workflow — the LLM node returns
    # estimated_ats_score_after on the improvements object (not a top-level key).
    imps = final.get("improvements") or {}
    overall = imps.get("estimated_ats_score_after", 0)
    assert 0 <= overall <= 100, f"score out of range: {overall}"
    assert overall >= 50, f"expected a well-scored resume, got {overall}"

    # LLM improvements were generated (populated, not empty fallback).
    assert imps.get("suggestions") or imps.get("rewritten_sections")
