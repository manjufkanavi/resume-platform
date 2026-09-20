#!/usr/bin/env python3
import subprocess, base64

hash = '[REDACTED-PASSWORD-HASH]'
uid = '[REDACTED-N8N_USER_ID]'

sql = "UPDATE public.user SET email='admin@iacgenie.com', \"firstName\"='Admin', \"lastName\"='User', password='%s' WHERE id='%s';" % (hash, uid)

b64 = base64.b64encode(sql.encode()).decode()
cmd = f'echo {b64} | base64 -d | docker exec -i iacgenie_postgres psql -U lightsrp -d lightsrp'
result = subprocess.run(
    ['ssh', '-o', 'ConnectTimeout=30', '-o', 'StrictHostKeyChecking=no',
     'mkanavi@192.168.0.118', cmd],
    capture_output=True, text=True, timeout=45
)
print(f"Update: {result.stdout} {result.stderr[:300]}")

# Verify
sql2 = "SELECT email, \"firstName\", \"lastName\" FROM public.user WHERE id='%s';" % uid
b64_2 = base64.b64encode(sql2.encode()).decode()
cmd2 = f'echo {b64_2} | base64 -d | docker exec -i iacgenie_postgres psql -U lightsrp -d lightsrp'
result2 = subprocess.run(
    ['ssh', '-o', 'ConnectTimeout=30', '-o', 'StrictHostKeyChecking=no',
     'mkanavi@192.168.0.118', cmd2],
    capture_output=True, text=True, timeout=45
)
print(f"Verify: {result2.stdout}")
