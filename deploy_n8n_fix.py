#!/usr/bin/env python3
"""Deploy fixed compose file to VM and restart n8n."""
import subprocess, base64, sys

# Read the local compose file
with open('/Users/manjunathkanavi/.hermes/git_clone_dir/resume-platform/docker-compose.resume-platform.yml', 'r') as f:
    content = f.read()

# Base64 encode
b64 = base64.b64encode(content.encode()).decode()

# Write to VM
write_cmd = f'echo {b64} | base64 -d > ~/docker/iacgenie/docker-compose.resume-platform.yml'
result = subprocess.run(
    ['ssh', '-o', 'ConnectTimeout=30', '-o', 'StrictHostKeyChecking=no',
     'mkanavi@192.168.0.118', write_cmd],
    capture_output=True, text=True, timeout=60
)
if result.returncode != 0:
    print(f"SSH error: {result.stderr[:500]}")
    sys.exit(1)

# Verify the fix
result2 = subprocess.run(
    ['ssh', '-o', 'ConnectTimeout=30', '-o', 'StrictHostKeyChecking=no',
     'mkanavi@192.168.0.118',
     'grep -E "QUEUE_BULL_REDIS_PASSWORD|env_file.*env" ~/docker/iacgenie/docker-compose.resume-platform.yml'],
    capture_output=True, text=True, timeout=45
)
print(f"Verification:\n{result2.stdout}")

# Restart n8n
print("Restarting n8n...")
result3 = subprocess.run(
    ['ssh', '-o', 'ConnectTimeout=30', '-o', 'StrictHostKeyChecking=no',
     'mkanavi@192.168.0.118',
     'cd ~/docker/iacgenie && docker compose -f docker-compose.resume-platform.yml up -d --force-recreate n8n 2>&1 | tail -5'],
    capture_output=True, text=True, timeout=60
)
print(result3.stdout)
if result3.stderr:
    print(f"STDERR: {result3.stderr[:300]}")
