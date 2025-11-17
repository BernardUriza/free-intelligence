#!/usr/bin/env python3
"""Debug CORS configuration on server"""
import paramiko

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)
    print("✅ Connected\n")

    # Check environment variable in process
    print("🔍 Checking ALLOWED_ORIGINS in backend process...")
    stdin, stdout, stderr = client.exec_command(
        "ps aux | grep 'uvicorn.*backend' | grep -v grep | awk '{print $2}' | xargs -I {} cat /proc/{}/environ | tr '\\0' '\\n' | grep ALLOWED"
    )
    output = stdout.read().decode()
    if output:
        print(f"✅ Found: {output}")
    else:
        print("❌ ALLOWED_ORIGINS not found in process environment")

    # Check .env file
    print("\n📋 Checking backend/.env file...")
    stdin, stdout, stderr = client.exec_command(
        "cat /opt/free-intelligence/backend/.env 2>/dev/null || echo 'No .env file'"
    )
    print(stdout.read().decode())

    # Check if backend can access the variable
    print("\n🧪 Testing with temporary Python script...")
    test_script = """
import os
import sys
sys.path.insert(0, '/opt/free-intelligence')
allowed = os.getenv("ALLOWED_ORIGINS", "NOT SET")
print(f"ALLOWED_ORIGINS from env: {allowed}")
print(f"Split result: {allowed.split(',')}")
"""

    stdin, stdout, stderr = client.exec_command(
        f"cd /opt/free-intelligence && python3 -c '{test_script}'"
    )
    print(stdout.read().decode())

    # Check backend startup logs
    print("\n📋 Recent backend logs:")
    stdin, stdout, stderr = client.exec_command("tail -30 /tmp/backend.log")
    print(stdout.read().decode())

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
finally:
    client.close()
