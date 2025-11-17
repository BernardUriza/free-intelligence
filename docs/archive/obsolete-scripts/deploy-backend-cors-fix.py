#!/usr/bin/env python3
"""Deploy backend CORS fix to production"""
import time

import paramiko

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"
LOCAL_FILE = "/Users/bernardurizaorozco/Documents/free-intelligence/backend/app/main.py"
REMOTE_FILE = "/opt/free-intelligence/backend/app/main.py"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)
    print("✅ Connected\n")

    # Upload updated main.py
    print("📤 Uploading updated main.py with CORS fix...")
    sftp = client.open_sftp()
    sftp.put(LOCAL_FILE, REMOTE_FILE)
    sftp.close()
    print("✅ Upload complete\n")

    # Verify file was uploaded
    print("🔍 Verifying upload...")
    stdin, stdout, stderr = client.exec_command(f"grep '104.131.175.65' {REMOTE_FILE}")
    if stdout.read().decode().strip():
        print("✅ Production origin found in uploaded file\n")
    else:
        print("❌ Production origin NOT found - upload may have failed\n")
        raise Exception("Upload verification failed")

    # Kill existing backend
    print("🛑 Stopping backend...")
    stdin, stdout, stderr = client.exec_command("pkill -f 'uvicorn.*backend' || true")
    stdout.channel.recv_exit_status()
    time.sleep(2)

    # Find the working directory and start backend
    print("🚀 Starting backend...")
    start_cmd = """
cd /opt/free-intelligence && \
nohup python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 7001 > /tmp/backend-cors-fixed.log 2>&1 &
"""

    stdin, stdout, stderr = client.exec_command(start_cmd)
    stdout.channel.recv_exit_status()

    print("⏳ Waiting for backend to start...")
    time.sleep(5)

    # Verify backend is running
    print("\n✅ Checking backend...")
    stdin, stdout, stderr = client.exec_command(
        "ps aux | grep uvicorn | grep backend | grep -v grep"
    )
    output = stdout.read().decode()

    if not output:
        print("❌ Backend not running!")
        print("\n📋 Startup log:")
        stdin, stdout, stderr = client.exec_command("cat /tmp/backend-cors-fixed.log")
        print(stdout.read().decode())
        raise Exception("Backend failed to start")

    print(f"✅ Backend running:\n{output}")

    # Wait for backend to be fully ready
    print("\n⏳ Waiting for backend to be ready...")
    time.sleep(3)

    # Test CORS
    print("\n🧪 Testing CORS...")
    test_cmd = 'curl -s -H "Origin: http://104.131.175.65" "http://localhost:7001/api/workflows/aurity/sessions?limit=1" -D - -o /dev/null 2>&1'

    stdin, stdout, stderr = client.exec_command(test_cmd)
    headers = stdout.read().decode()

    print("Response headers:")
    print(headers)

    if "access-control-allow-origin" in headers.lower():
        print("\n✅ SUCCESS! CORS is now configured correctly!")
    else:
        print("\n⚠️  access-control-allow-origin header still missing")
        print("\n📋 Backend log:")
        stdin, stdout, stderr = client.exec_command("tail -50 /tmp/backend-cors-fixed.log")
        print(stdout.read().decode())

    print("\n╔════════════════════════════════════════════╗")
    print("║      ✅ BACKEND DEPLOYED & RESTARTED!      ║")
    print("╚════════════════════════════════════════════╝")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
finally:
    client.close()
