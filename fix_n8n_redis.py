#!/usr/bin/env python3
"""Read .env from VM, fix compose file, and redeploy n8n."""
import subprocess, base64, sys

# Step 1: Read the .env file from VM to get REDIS_PASSWORD
result = subprocess.run(
    ['ssh', '-o', 'ConnectTimeout=30', '-o', 'StrictHostKeyChecking=no',
     'mkanavi@192.168.0.118',
     'grep "^REDIS_PASSWORD=" ~/docker/iacgenie/.env | cut -d= -f2-'],
    capture_output=True, text=True, timeout=45
)
redis_pass = result.stdout.strip()
print(f"REDIS_PASSWORD length: {len(redis_pass)}")

# Step 2: Read the local compose file
with open('/Users/manjunathkanavi/.hermes/git_clone_dir/resume-platform/docker-compose.resume-platform.yml', 'r') as f:
    content = f.read()

# Step 3: Fix the n8n environment section
# Replace the QUEUE_BULL_REDIS_PORT line to add the password
old = '      - QUEUE_BULL_REDIS_PORT=6379\n      - OLLAMA_URL=http://ollama:11434'
new = f'      - QUEUE_BULL_REDIS_PORT=6379\n      - QUEUE_BULL_REDIS_PASSWORD={redis_pass}\n      - OLLAMA_URL=http://ollama:11434'

if old in content:
    content = content.replace(old, new)
    print("Fixed: added QUEUE_BULL_REDIS_PASSWORD with actual value")
else:
    print("WARNING: Pattern not found in local compose")
    # Try to find what's there
    import re
    m = re.search(r'QUEUE_BULL_REDIS_PORT.*?OLLAMA_URL', content, re.DOTALL)
    if m:
        print(f"Found: {repr(m.group()[:200])}")

# Step 4: Also fix the VM file directly (bypass compose variable expansion)
vm_content = content
# Write to VM via base64
b64 = base64.b64encode(vm_content.encode()).decode()
write_cmd = f'echo {b64} | base64 -d > ~/docker/iacgenie/docker-compose.resume-platform.yml'

result2 = subprocess.run(
    ['ssh', '-o', 'ConnectTimeout=30', '-o', 'StrictHostKeyChecking=no',
     'mkanavi@192.168.0.118', write_cmd],
    capture_output=True, text=True, timeout=60
)
if result2.returncode != 0:
    print(f"SSH write error: {result2.stderr[:300]}")
    sys.exit(1)

# Step 5: Verify
result3 = subprocess.run(
    ['ssh', '-o', 'ConnectTimeout=30', '-o', 'StrictHostKeyChecking=no',
     'mkanavi@192.168.0.118',
     'grep QUEUE_BULL_REDIS ~/docker/iacgenie/docker-compose.resume-platform.yml'],
    capture_output=True, text=True, timeout=45
)
print(f"VM compose n8n Redis config:\n{result3.stdout}")

# Step 6: Restart n8n
print("\nRestarting n8n...")
result4 = subprocess.run(
    ['ssh', '-o', 'ConnectTimeout=30', '-o', 'StrictHostKeyChecking=no',
     'mkanavi@192.168.0.118',
     'cd ~/docker/iacgenie && docker compose -f docker-compose.resume-platform.yml up -d --force-recreate n8n 2>&1 | tail -3'],
    capture_output=True, text=True, timeout=60
)
print(result4.stdout)
if result4.stderr:
    print(f"STDERR: {result4.stderr[:200]}")
