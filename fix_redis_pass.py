#!/usr/bin/env python3
import subprocess

# Read the compose file
with open('/Users/manjunathkanavi/.hermes/git_clone_dir/resume-platform/docker-compose.resume-platform.yml', 'r') as f:
    content = f.read()

# Fix: add QUEUE_BULL_REDIS_PASSWORD to n8n environment
old = '      - QUEUE_BULL_REDIS_PORT=6379\n      - OLLAMA_URL=http://ollama:11434'
new = '      - QUEUE_BULL_REDIS_PORT=6379\n      - QUEUE_BULL_REDIS_PASSWORD=${REDIS_PASSWORD}\n      - OLLAMA_URL=http://ollama:11434'

if old in content:
    content = content.replace(old, new)
    print("Fixed: added QUEUE_BULL_REDIS_PASSWORD")
else:
    print("Pattern not found, checking...")
    # Check what's actually there
    import re
    m = re.search(r'QUEUE_BULL_REDIS_PORT.*?OLLAMA_URL', content, re.DOTALL)
    if m:
        print(f"Found: {repr(m.group())}")
    else:
        print("Could not find pattern")

# Write back
with open('/Users/manjunathkanavi/.hermes/git_clone_dir/resume-platform/docker-compose.resume-platform.yml', 'w') as f:
    f.write(content)

# Also fix the VM file directly
vm_cmd = '''python3 -c "
p = '/home/mkanavi/docker/iacgenie/docker-compose.resume-platform.yml'
with open(p) as f: c = f.read()
c = c.replace('QUEUE_BULL_REDIS_PASSWORD=*** ', 'QUEUE_BULL_REDIS_PASSWORD=\${REDIS_PASSWORD}')
with open(p, 'w') as f: f.write(c)
print('VM fixed')
"'''

result = subprocess.run(
    ['ssh', '-o', 'ConnectTimeout=30', '-o', 'StrictHostKeyChecking=no',
     'mkanavi@192.168.0.118', vm_cmd],
    capture_output=True, text=True, timeout=45
)
print(f"VM result: {result.stdout} {result.stderr[:200]}")
