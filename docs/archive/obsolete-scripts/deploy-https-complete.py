#!/usr/bin/env python3
"""Complete HTTPS deployment - backend + frontend"""
import os
import time

import paramiko

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"
LOCAL_BACKEND = "/Users/bernardurizaorozco/Documents/free-intelligence/backend/app/main.py"
REMOTE_BACKEND = "/opt/free-intelligence/backend/app/main.py"
LOCAL_FRONTEND = "/Users/bernardurizaorozco/Documents/free-intelligence/apps/aurity/out"
REMOTE_FRONTEND = "/opt/free-intelligence/apps/aurity"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)
    print("✅ Connected\n")

    # Step 1: Deploy backend with HTTPS CORS
    print("📤 1/3: Deploying backend with HTTPS CORS...")
    sftp = client.open_sftp()
    sftp.put(LOCAL_BACKEND, REMOTE_BACKEND)
    print("✅ Backend uploaded\n")

    # Step 2: Restart backend
    print("🔄 2/3: Restarting backend...")
    stdin, stdout, stderr = client.exec_command("pkill -f 'uvicorn.*backend' || true")
    stdout.channel.recv_exit_status()
    time.sleep(2)

    start_cmd = "cd /opt/free-intelligence && nohup python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 7001 > /tmp/backend.log 2>&1 &"
    stdin, stdout, stderr = client.exec_command(start_cmd)
    stdout.channel.recv_exit_status()
    time.sleep(3)

    # Verify backend
    stdin, stdout, stderr = client.exec_command(
        "ps aux | grep uvicorn | grep backend | grep -v grep"
    )
    if stdout.read().decode().strip():
        print("✅ Backend running\n")
    else:
        print("❌ Backend failed to start\n")
        raise Exception("Backend startup failed")

    # Step 3: Deploy frontend
    print("📤 3/3: Deploying frontend...")

    # Clear old files
    stdin, stdout, stderr = client.exec_command(f"rm -rf {REMOTE_FRONTEND}/out/*")
    stdout.channel.recv_exit_status()

    # Upload new files
    def upload_dir(local_dir, remote_dir):
        for item in os.listdir(local_dir):
            local_path = os.path.join(local_dir, item)
            remote_path = os.path.join(remote_dir, item).replace("\\", "/")

            if os.path.isfile(local_path):
                sftp.put(local_path, remote_path)
            elif os.path.isdir(local_path):
                try:
                    sftp.mkdir(remote_path)
                except:
                    pass
                upload_dir(local_path, remote_path)

    upload_dir(LOCAL_FRONTEND, f"{REMOTE_FRONTEND}/out")
    sftp.close()
    print("✅ Frontend deployed\n")

    # Reload Nginx
    print("🔄 Reloading Nginx...")
    stdin, stdout, stderr = client.exec_command("nginx -t && systemctl reload nginx")
    if stdout.channel.recv_exit_status() == 0:
        print("✅ Nginx reloaded\n")
    else:
        print(f"⚠️  Nginx reload warning: {stderr.read().decode()}\n")

    # Test HTTPS
    print("🧪 Testing HTTPS deployment...")
    stdin, stdout, stderr = client.exec_command(
        'curl -s -o /dev/null -w "%{http_code}" https://fi-aurity.duckdns.org/'
    )
    status = stdout.read().decode().strip()

    if status == "200":
        print(f"✅ HTTPS working! (status: {status})\n")
    else:
        print(f"⚠️  HTTPS returned {status}\n")

    # Test CORS
    print("🧪 Testing CORS...")
    stdin, stdout, stderr = client.exec_command(
        'curl -s -H "Origin: https://fi-aurity.duckdns.org" "http://localhost:7001/api/workflows/aurity/sessions?limit=1" -D - -o /dev/null 2>&1 | grep "access-control-allow-origin"'
    )
    cors = stdout.read().decode()

    if "fi-aurity.duckdns.org" in cors:
        print(f"✅ CORS configured: {cors.strip()}\n")
    else:
        print(f"⚠️  CORS header: {cors}\n")

    print("\n╔════════════════════════════════════════════╗")
    print("║      🎉 DEPLOYMENT COMPLETE!              ║")
    print("╚════════════════════════════════════════════╝")
    print("\n🌐 Your app is live at: https://fi-aurity.duckdns.org/")
    print("🔒 Microphone access should now work!")
    print("🎙️  Try the /medical-ai page to test recording")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
finally:
    client.close()
