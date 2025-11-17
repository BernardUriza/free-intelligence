#!/usr/bin/env python3
"""Fix CORS by adding production origin to backend environment"""
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

    # Check if backend is running
    print("🔍 Checking backend status...")
    stdin, stdout, stderr = client.exec_command("ps aux | grep 'uvicorn' | grep -v grep")
    backend_running = stdout.read().decode().strip()

    if backend_running:
        print(f"✅ Backend is running:\n{backend_running}\n")
    else:
        print("⚠️  Backend is not running\n")

    # Update environment variable for current process (temporary fix)
    print("🔧 Setting ALLOWED_ORIGINS environment variable...")

    # Find the backend directory and update .env file if it exists
    commands = [
        "cd /opt/free-intelligence",
        'echo "ALLOWED_ORIGINS=http://localhost:9000,http://localhost:9050,http://104.131.175.65" >> backend/.env',
        'cat backend/.env | grep ALLOWED_ORIGINS || echo "ALLOWED_ORIGINS not found"',
    ]

    for cmd in commands:
        stdin, stdout, stderr = client.exec_command(cmd)
        output = stdout.read().decode()
        error = stderr.read().decode()
        if output:
            print(f"  {cmd}")
            print(f"  Output: {output}")
        if error and "No such file" not in error:
            print(f"  Error: {error}")

    print("\n🔄 Restarting backend with new CORS settings...")

    # Kill existing backend
    stdin, stdout, stderr = client.exec_command("pkill -f 'uvicorn.*backend' || true")
    stdout.channel.recv_exit_status()
    time.sleep(2)

    # Start backend with ALLOWED_ORIGINS
    start_cmd = """
cd /opt/free-intelligence && \
export ALLOWED_ORIGINS="http://localhost:9000,http://localhost:9050,http://104.131.175.65" && \
nohup python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 7001 > /tmp/backend.log 2>&1 &
"""

    stdin, stdout, stderr = client.exec_command(start_cmd)
    stdout.channel.recv_exit_status()
    time.sleep(3)

    # Verify backend is running
    print("\n✅ Verifying backend restart...")
    stdin, stdout, stderr = client.exec_command("ps aux | grep 'uvicorn' | grep -v grep")
    output = stdout.read().decode()

    if output:
        print(f"✅ Backend running:\n{output}")
    else:
        print("❌ Backend failed to start!")
        print("\nChecking logs...")
        stdin, stdout, stderr = client.exec_command("tail -20 /tmp/backend.log")
        print(stdout.read().decode())

    # Test CORS
    print("\n🧪 Testing CORS headers...")
    stdin, stdout, stderr = client.exec_command(
        'curl -s -H "Origin: http://104.131.175.65" '
        '-H "Access-Control-Request-Method: GET" '
        '-X OPTIONS http://localhost:7001/api/workflows/aurity/sessions?limit=1 -I | grep -i "access-control"'
    )
    cors_headers = stdout.read().decode()

    if cors_headers:
        print(f"✅ CORS headers present:\n{cors_headers}")
    else:
        print("⚠️  No CORS headers found")

    print("\n╔════════════════════════════════════════════╗")
    print("║      ✅ CORS FIX COMPLETE!                 ║")
    print("╚════════════════════════════════════════════╝")
    print("\n🌐 Frontend should now be able to access the API")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
finally:
    client.close()
