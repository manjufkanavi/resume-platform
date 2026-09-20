#!/usr/bin/env python3
"""Fix n8n on VM: fix compose, start container, wait for health."""

import subprocess
import sys

VM = "mkanavi@192.168.0.118"
WORKDIR = "~/docker/iacgenie"

def ssh(cmd):
    r = subprocess.run(
        ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=15", VM, cmd],
        capture_output=True, text=True, timeout=30
    )
    return r.returncode, r.stdout.strip(), r.stderr.strip()

# Step 1: Kill any stale n8n container
print("== Stopping old n8n ==")
ssh(f"docker -c {WORKDIR} compose stop n8n 2>/dev/null; docker rm -f iacgenie_n8n 2>/dev/null")

# Step 2: Fix env_file path in compose — ./.env -> ../.env
print("== Fixing env_file path ==")
rc, out, err = ssh(f"sed -i 's|      - ./.env|      - ../.env|' {WORKDIR}/docker-compose.resume-platform.yml")
print(f"  sed rc={rc}")

# Step 3: Fix DB name — lightsrp -> n8n
print("== Fixing DB name ==")
rc, out, err = ssh(f"sed -i 's|DB_POSTGRESDB_DATABASE=lightsrp|DB_POSTGRESDB_DATABASE=n8n|' {WORKDIR}/docker-compose.resume-platform.yml")
print(f"  sed rc={rc}")

# Step 4: Verify the fix
print("== Verifying compose ==")
rc, out, err = ssh(f"grep -n 'env_file\\|DB_POSTGRESDB_DATABASE' {WORKDIR}/docker-compose.resume-platform.yml")
print(f"  {out}")

# Step 5: Start n8n (force recreate to pick up changes)
print("== Starting n8n ==")
rc, out, err = ssh(f"cd {WORKDIR} && docker compose -f docker-compose.resume-platform.yml up -d --force-recreate n8n 2>&1")
print(f"  rc={rc}")

# Step 6: Wait for health (poll up to 5 min)
print("== Waiting for n8n healthy ==")
for i in range(60):
    rc, out, err = ssh("docker inspect --format='{{.State.Health.Status}}' iacgenie_n8n 2>/dev/null")
    if "healthy" in out:
        print(f"  ✅ n8n healthy after {i+1} checks")
        break
    if "not running" in out or rc != 0:
        # Show logs for debugging
        print(f"  ❌ n8n not healthy: {out}")
        rc, logs, _ = ssh("docker logs iacgenie_n8n --tail 30")
        print(f"  logs: {logs[:500]}")
        sys.exit(1)
    if i % 5 == 4:
        print(f"  waiting... ({i+1}/60)")
    import time; time.sleep(5)

print("== DONE ==")
