#!/usr/bin/env python3
"""Generate docker-compose.resume-platform.yml on the VM."""
import base64, subprocess, sys

# Read the local compose file
with open('/Users/manjunathkanavi/.hermes/git_clone_dir/resume-platform/docker-compose.resume-platform.yml', 'r') as f:
    content = f.read()

# Base64 encode and send via SSH
b64 = base64.b64encode(content.encode()).decode()

# Write directly on VM
cmd = f'''echo {b64} | base64 -d > ~/docker/iacgenie/docker-compose.resume-platform.yml'''
result = subprocess.run(
    ['ssh', '-o', 'ConnectTimeout=30', '-o', 'StrictHostKeyChecking=no',
     'mkanavi@192.168.0.118', cmd],
    capture_output=True, text=True, timeout=60
)
if result.returncode != 0:
    print(f"SSH error: {result.stderr[:500]}")
    sys.exit(1)

# Verify
result2 = subprocess.run(
    ['ssh', '-o', 'ConnectTimeout=30', '-o', 'StrictHostKeyChecking=no',
     'mkanavi@192.168.0.118',
     'grep -c "wget.*healthz" ~/docker/iacgenie/docker-compose.resume-platform.yml'],
    capture_output=True, text=True, timeout=30
)
print(f"Health check fix present: {'YES' if result2.stdout.strip() == '1' else 'NO'}")
print(f"Compose file size: {subprocess.run(['ssh', '-o', 'ConnectTimeout=30', '-o', 'StrictHostKeyChecking=no', 'mkanavi@192.168.0.118', 'wc -c ~/docker/iacgenie/docker-compose.resume-platform.yml'], capture_output=True, text=True, timeout=30).stdout.strip()}")

# Restart n8n
print("\nRestarting n8n...")
result3 = subprocess.run(
    ['ssh', '-o', 'ConnectTimeout=30', '-o', 'StrictHostKeyChecking=no',
     'mkanavi@192.168.0.118',
     'cd ~/docker/iacgenie && docker compose -f docker-compose.resume-platform.yml up -d n8n'],
    capture_output=True, text=True, timeout=60
)
print(result3.stdout[:500])
if result3.stderr:
    print(f"STDERR: {result3.stderr[:200]}")
