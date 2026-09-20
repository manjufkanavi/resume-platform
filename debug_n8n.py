#!/usr/bin/env python3
"""Debug n8n auth and try to set up first user + activate workflow."""

import base64
import json
import subprocess


VM = "mkanavi@192.168.0.118"


def run(cmd, timeout=30):
    return subprocess.run(
        ["ssh", "-o", "ConnectTimeout=15", "-o", "StrictHostKeyChecking=no", VM, cmd],
        capture_output=True, text=True, timeout=timeout,
    )


def main():
    # 1. Check n8n config file
    print("=== N8N Config ===")
    r = run('docker exec iacgenie_n8n cat /home/node/.n8n/config 2>&1')
    print(r.stdout[:500])

    # 2. Check n8n env
    print("\n=== N8N Environment ===")
    r = run('docker exec iacgenie_n8n env 2>&1')
    for line in r.stdout.split('\n'):
        if any(kw in line.lower() for kw in ['auth', 'api', 'key', 'secret', 'user', 'password']):
            print(line)

    # 3. Check if n8n has been initialized (first-run setup needed?)
    print("\n=== N8N Init State ===")
    
    # Check if there's a session/cookie auth issue  
    r = run('curl -sv "http://127.0.0.1:3005/api/v1/workflows" 2>&1 | grep -i "set-cookie\|authorization\\|api-key"')
    print("Cookie/Auth headers:", r.stdout[:300])

    # Try to create a workflow via the webhook URL directly (the endpoint is public)
    print("\n=== Testing Webhook Trigger ===")
    
    # The webhook path is /resume-upload - check if it's accessible without auth  
    r = run('curl -s "http://127.0.0.1:3005/webhook/resume-upload" -X POST')
    print("Webhook trigger:", r.stdout[:300])

    # 4. Check if n8n has a setup flow we need to complete
    print("\n=== Checking Setup Flow ===")
    
    # Try the owner creation endpoint  
    r = run('curl -s "http://127.0.0.1:3005/api/v1/owner" -X POST -H "Content-Type: application/json" \\\n      -d \'{"email": "admin@iacgenie.com", "password": "[REDACTED-N8N_ADMIN_PASSWORD]", "firstName": "Admin", "lastName": "User"}\'')
    print("Create owner:", r.stdout[:300])

    # 5. Try with session cookie approach
    print("\n=== Cookie-based Auth ===")
    
    # Login as owner if created above  
    r = run('curl -s "http://127.0.0.1:3005/api/v1/auth/login" -X POST \\\n      -H "Content-Type: application/json" \\\n      -d \'{"email": "admin@iacgenie.com", "password": "[REDACTED-N8N_ADMIN_PASSWORD]"}\'')
    print("Login:", r.stdout[:300])

    # 6. Direct database check - is the user_api_key linked to a valid user?
    print("\n=== User API Key DB Check ===")
    
    # Get the userId from user_api_keys  
    r = run('docker exec -i iacgenie_postgres psql -U lightsrp -d n8n \\\n      -c "SELECT userId, label FROM user_api_keys;"')
    print("API keys:", r.stdout[:300])

    # Check if that userId exists in the user table
    r = run('docker exec -i iacgenie_postgres psql -U lightsrp -d n8n \\\n      -c "SELECT * FROM user_api_keys;"')
    print("Full API key record:", r.stdout[:300])


if __name__ == "__main__":
    main()
