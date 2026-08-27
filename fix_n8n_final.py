#!/usr/bin/env python3
"""Fix n8n Redis password in compose file and redeploy."""
import subprocess, sys

# Read the local compose file
with open('/Users/manjunathkanavi/.hermes/git_clone_dir/resume-platform/docker-compose.resume-platform.yml', 'r') as f:
    content = f.read()

# Fix: replace empty QUEUE_BULL_REDIS_PASSWORD with env var reference
old = '      - QUEUE_BULL_REDIS_PASSWORD=\n'
new = '      - QUEUE_BULL_REDIS_PASSWORD=${REDIS_PASSWORD}\n'

if old in content:
    content = content.replace(old, new)
    print("Fixed: QUEUE_BULL_REDIS_PASSWORD=${REDIS_PASSWORD}")
else:
    # Try to find what's there
    import re
    m = re.search(r'QUEUE_BULL_REDIS_PASSWORD.*\n', content)
    if m:
        print(f"Found: {repr(m.group())}")
    else:
        print("Could not find QUEUE_BULL_REDIS_PASSWORD")

# Write back
with open('/Users/manjunathkanavi/.hermes/git_clone_dir/resume-platform/docker-compose.resume-platform.yml', 'w') as f:
    f.write(content)

# Deploy to VM using Python script approach (smaller payload)
script = '''
p = '/home/mkanavi/docker/iacgenie/docker-compose.resume-platform.yml'
with open(p) as f: c = f.read()
c = c.replace('QUEUE_BULL_REDIS_PASSWORD=\\n', 'QUEUE_BULL_REDIS_PASSWORD=${REDIS_PASSWORD}\\n')
with open(p, 'w') as f: f.write(c)
print('VM fixed')
'''

# Write script to VM
result = subprocess.run(
    ['ssh', '-o', 'ConnectTimeout=30', '-o', 'StrictHostKeyChecking=no',
     'mkanavi@192.168.0.118',
     f'python3 << \'PYEOF\'\n{script}\nPYEOF'],
    capture_output=True, text=True, timeout=45
)
print(f"VM script: {result.stdout} {result.stderr[:200]}")

# Verify
result2 = subprocess.run(
    ['ssh', '-o', 'ConnectTimeout=30', '-o', 'StrictHostKeyChecking=no',
     'mkanavi@192.168.0.118',
     'grep QUEUE_BULL_REDIS ~/docker/iacgenie/docker-compose.resume-platform.yml'],
    capture_output=True, text=True, timeout=45
)
print(f"VM config:\n{result2.stdout}")

# Restart n8n
print("Restarting n8n...")
result3 = subprocess.run(
    ['ssh', '-o', 'ConnectTimeout=30', '-o', 'StrictHostKeyChecking=no',
     'mkanavi@192.168.0.118',
     'cd ~/docker/iacgenie && docker compose -f docker-compose.resume-platform.yml up -d --force-recreate n8n 2>&1 | tail -3'],
    capture_output=True, text=True, timeout=60
)
print(result3.stdout)
