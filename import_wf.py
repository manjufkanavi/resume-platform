#!/usr/bin/env python3
import json, uuid

with open('/tmp/resume-pipeline.json') as f:
    wf = json.load(f)

wid = str(uuid.uuid4())
vid = wid  # same UUID for both tables

nodes_json = json.dumps(wf['nodes'])
connections_json = json.dumps(wf['connections'])

def pg_escape(s):
    return s.replace('\\', '\\\\').replace("'", "''")

nodes_esc = pg_escape(nodes_json)
conn_esc = pg_escape(connections_json)

# Use string concatenation to avoid f-string quote conflicts
sql = (
    'INSERT INTO workflow_entity ("id", name, active, nodes, connections, "createdAt", "updatedAt", "versionId", "triggerCount")\n'
    + "VALUES ('" + wid + "', '" + wf['name'] + "', false, E'"
    + nodes_esc + "', E'" + conn_esc + "', NOW(), NOW(), '" + vid
    + "', 0);\n\n"

    'INSERT INTO workflow_history ("versionId", "workflowId", authors, "createdAt", "updatedAt", nodes, connections, name)\n'
    + "VALUES ('" + vid + "', '" + wid + "', 'admin', NOW(), NOW(), E'"
    + nodes_esc + "', E'" + conn_esc + "', '" + wf['name'] + "');\n\n"

    'SELECT id FROM workflow_entity;\n'
)

print(sql, end='')
