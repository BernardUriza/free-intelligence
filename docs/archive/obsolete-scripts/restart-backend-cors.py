#!/usr/bin/env python3
"""Restart backend with CORS properly configured"""
import time

import paramiko

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)
    print("✅ Connected\n")

    # Find the actual python/uvicorn being used
    print("🔍 Finding current backend process...")
    stdin, stdout, stderr = client.exec_command(
        "ps aux | grep uvicorn | grep backend | grep -v grep"
    )
    current_process = stdout.read().decode().strip()
    print(f"Current: {current_process}\n")

    # Kill existing backend
    print("🛑 Stopping backend...")
    stdin, stdout, stderr = client.exec_command("pkill -f 'uvicorn.*backend'")
    stdout.channel.recv_exit_status()
    time.sleep(2)

    # Find Python executable with uvicorn
    print("🔍 Finding Python with uvicorn...")
    stdin, stdout, stderr = client.exec_command("which python")
    python_path = stdout.read().decode().strip()
    print(f"Python: {python_path}")

    # Start backend with explicit CORS origins in command
    print("\n🚀 Starting backend with CORS...")

    start_cmd = f"""
cd /opt/free-intelligence && \
ALLOWED_ORIGINS="http://localhost:9000,http://localhost:9050,http://104.131.175.65" \
nohup {python_path} -m uvicorn backend.app.main:app --host 0.0.0.0 --port 7001 > /tmp/backend-cors.log 2>&1 &
"""

    stdin, stdout, stderr = client.exec_command(start_cmd)
    stdout.channel.recv_exit_status()

    print("Waiting for backend to start...")
    time.sleep(5)

    # Verify backend is running
    print("\n✅ Checking backend process...")
    stdin, stdout, stderr = client.exec_command(
        "ps aux | grep uvicorn | grep backend | grep -v grep"
    )
    output = stdout.read().decode()

    if output:
        print(f"✅ Backend running:\n{output}")
    else:
        print("❌ Backend failed to start!")
        print("\n📋 Checking startup logs...")
        stdin, stdout, stderr = client.exec_command("cat /tmp/backend-cors.log")
        print(stdout.read().decode())
        raise Exception("Backend startup failed")

    # Test CORS after startup
    print("\n⏳ Waiting for backend to be ready...")
    time.sleep(3)

    print("\n🧪 Testing CORS headers...")
    test_cmd = '''curl -s -H "Origin: http://104.131.175.65" "http://localhost:7001/api/workflows/aurity/sessions?limit=1" -D - -o /dev/null 2>&1 | grep -i "access-control"'''

    stdin, stdout, stderr = client.exec_command(test_cmd)
    cors_output = stdout.read().decode()

    if "access-control-allow-origin" in cors_output.lower():
        print(f"✅ CORS configured correctly:\n{cors_output}")
    else:
        print(f"⚠️  CORS headers found but access-control-allow-origin missing:\n{cors_output}")
        print("\n📋 Backend startup log:")
        stdin, stdout, stderr = client.exec_command("head -50 /tmp/backend-cors.log")
        print(stdout.read().decode())

    print("\n╔════════════════════════════════════════════╗")
    print("║      ✅ BACKEND RESTARTED!                 ║")
    print("╚════════════════════════════════════════════╝")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
finally:
    client.close()
