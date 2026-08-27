import subprocess, sys

# Read the compose file
with open('/Users/manjunathkanavi/.hermes/git_clone_dir/resume-platform/docker-compose.resume-platform.yml', 'r') as f:
    content = f.read()

# Fix the n8n health check
old = '''    healthcheck:
      test: ["CMD-SHELL", "exec 6<>/dev/tcp/127.0.0.1:5678 && exec 6>&-"]'''
new = '''    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://127.0.0.1:5678/healthz || exit 1"]'''

if old in content:
    content = content.replace(old, new)
    print("Fixed n8n health check")
else:
    print("WARNING: Could not find n8n health check pattern")
    # Try to find it
    import re
    match = re.search(r'healthcheck:.*?test:.*?\n.*?"CMD-SHELL".*?5678', content, re.DOTALL)
    if match:
        print(f"Found at: {match.group()[:100]}")
    sys.exit(1)

# Write back
with open('/Users/manjunathkanavi/.hermes/git_clone_dir/resume-platform/docker-compose.resume-platform.yml', 'w') as f:
    f.write(content)

print("Done")
