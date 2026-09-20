#!/usr/bin/env python3
import subprocess, base64, uuid

api_key = '[REDACTED-N8N_API_KEY]'  # was a live n8n API key; set via env at runtime
user_id = '[REDACTED-N8N_USER_ID]'  # was a live n8n user UUID
key_id = str(uuid.uuid4())

sql = f"""INSERT INTO user_api_keys (id, "userId", label, "apiKey", scopes, audience)
VALUES ('{key_id}', '{user_id}', 'resume-api', '{api_key}', '["default"]', 'resume-platform');"""

b64 = base64.b64encode(sql.encode()).decode()
cmd = f'echo {b64} | base64 -d | docker exec -i iacgenie_postgres psql -U lightsrp -d lightsrp'
result = subprocess.run(
    ['ssh', '-o', 'ConnectTimeout=30', '-o', 'StrictHostKeyChecking=no',
     'mkanavi@192.168.0.118', cmd],
    capture_output=True, text=True, timeout=45
)
print(f"Insert: {result.stdout} {result.stderr[:300]}")

# Verify
sql2 = "SELECT id, label, substring(\"apiKey\",1,20) FROM user_api_keys;"
b64_2 = base64.b64encode(sql2.encode()).decode()
cmd2 = f'echo {b64_2} | base64 -d | docker exec -i iacgenie_postgres psql -U lightsrp -d lightsrp'
result2 = subprocess.run(
    ['ssh', '-o', 'ConnectTimeout=30', '-o', 'StrictHostKeyChecking=no',
     'mkanavi@192.168.0.118', cmd2],
    capture_output=True, text=True, timeout=45
)
print(f"Verify: {result2.stdout}")
