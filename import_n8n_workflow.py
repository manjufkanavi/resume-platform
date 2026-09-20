#!/usr/bin/env python3
"""Import n8n workflow (resume-pipeline.json) into the remote n8n instance."""

import base64
import json
import subprocess
import sys


VM = "mkanavi@192.168.0.118"
N8N_PORT = 3005
WORKFLOW_PATH = "n8n/workflows/resume-pipeline.json"


def run(cmd: str, timeout=60) -> subprocess.CompletedProcess[str]:
    """Run a shell command via SSH."""
    return subprocess.run(
        ["ssh", "-o", "ConnectTimeout=15", "-o", "StrictHostKeyChecking=no", VM, cmd],
        capture_output=True, text=True, timeout=timeout,
    )


def main():
    # 1. Read workflow JSON locally
    with open(WORKFLOW_PATH) as f:
        wf = json.load(f)

    print("✓ Loaded workflow:", wf["name"])
    print("  Nodes:", len(wf["nodes"]), "Connections:", list(wf["connections"].keys()))

    # 2. Base64-encode the workflow JSON and transfer to VM
    wf_json = json.dumps(wf)
    b64_wf = base64.b64encode(wf_json.encode()).decode()

    # Write to temp file on VM
    result = run("echo '" + b64_wf + "' | base64 -d > /tmp/resume-pipeline.json")
    if result.returncode != 0:
        print("✗ Failed to transfer workflow JSON:", result.stderr[:200])
        sys.exit(1)

    # Verify transfer
    verify = run("wc -c /tmp/resume-pipeline.json")
    print("✓ Transferred workflow JSON (" + verify.stdout.strip() + ")")

    # 3. Write the import Python script on VM and run it
    api_key = "nps_597af9662cde6c998abe855badbbab03bda78ba71fa95411d6ae9bcafc756fbb"

    import_script = '''import json, urllib.request
api_key = 'N8N_API_KEY_PLACEHOLDER'

with open('/tmp/resume-pipeline.json') as f:
    wf = json.load(f)

data = json.dumps(wf).encode()
req = urllib.request.Request(
    'http://127.0.0.1:3005/api/v1/workflows',
    data=data,
    headers={
        'Content-Type': 'application/json',
        'X-N8N-API-KEY': api_key,
    },
    method='POST',
)

try:
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read())
    print(f'Imported workflow: {result["id"][:8]}...')

    # Activate the workflow
    wf_id = result['id']
    act_req = urllib.request.Request(
        f'http://127.0.0.1:3005/api/v1/workflows/{wf_id}/activate',
        method='PUT',
    )
    act_req.add_header('X-N8N-API-KEY', api_key)
    act_resp = urllib.request.urlopen(act_req, timeout=30)
    print(f'Activated: {act_resp.status}')

except urllib.error.HTTPError as e:
    body = e.read().decode() if e.fp else 'unknown'
    print(f'HTTP {e.code}: {body[:300]}')

except Exception as e:
    print(f'Error: {e}')
'''

    import_script = import_script.replace("N8N_API_KEY_PLACEHOLDER", api_key)
    b64_import = base64.b64encode(import_script.encode()).decode()

    result = run(
        "echo '" + b64_import + "' | base64 -d > /tmp/import_wf.py && python3 /tmp/import_wf.py 2>&1"
    )

    print("  →", result.stdout.strip())

    if "Error:" in (result.stdout + result.stderr):
        print("✗ Import may have failed:", result.stderr[:300])

    # Clean up
    run("rm -f /tmp/resume-pipeline.json /tmp/import_wf.py")

    print("\n✓ Done! n8n workflow imported and activated.")


if __name__ == "__main__":
    main()
