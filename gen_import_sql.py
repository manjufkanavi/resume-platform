#!/usr/bin/env python3
"""Generate SQL to insert n8n v2.x workflow into DB."""

import json, uuid, sys
from datetime import datetime, timezone

with open('n8n/workflows/resume-pipeline.json') as f:
    wf = json.load(f)

workflow_id = str(uuid.uuid4())
versionId = workflow_id  # same UUID for simplicity

# Escape JSON strings for SQL - wrap in single quotes, escape inner quotes
nodes_json = json.dumps(wf['nodes'], ensure_ascii=False)
connections_json = json.dumps(wf['connections'], ensure_ascii=False)

# Escape for SQL (double single-quotes, wrap in $$...$$ to avoid escaping issues)
nodes_escaped = nodes_json.replace("'", "''")
connections_escaped = connections_json.replace("'", "''")

now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S+00')

sql = f"""-- n8n v2.x workflow import: Resume Processing Pipeline
INSERT INTO workflow_history (versionId, "workflowId", authors, createdAt, updatedAt, nodes, connections, name, autosaved, description, nodeGroups)
VALUES (
  '{versionId}',
  '{workflow_id}',
  'admin',
  '{now}',
  '{now}',
  $${nodes_escaped}$$,
  $${connections_escaped}$$,
  '{wf['name']}',
  false,
  'ATS/LLM resume processing pipeline',
  $${json.dumps(wf.get('nodeGroups', []), ensure_ascii=False)}$$
);

INSERT INTO workflow_entity (id, name, active, nodes, connections, createdAt, updatedAt, versionId, triggerCount, isArchived, versionCounter, description)
VALUES (
  '{workflow_id}',
  '{wf['name']}',
  false,
  $${nodes_escaped}$$,
  $${connections_escaped}$$,
  '{now}',
  '{now}',
  '{versionId}',
  0,
  false,
  1,
  'ATS/LLM resume processing pipeline'
);

SELECT '{workflow_id}' as workflow_id, versionId FROM workflow_entity WHERE id='{workflow_id}';
"""

print(sql)
