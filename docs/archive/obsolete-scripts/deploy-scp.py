#!/usr/bin/env python3
"""Deploy static frontend via SCP"""
import os
import time

import paramiko

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"
LOCAL_OUT_DIR = "/Users/bernardurizaorozco/Documents/free-intelligence/apps/aurity/out"
REMOTE_DIR = "/opt/free-intelligence/apps/aurity"

print("🔐 Connecting to server...")

# Retry connection
max_retries = 10
for attempt in range(max_retries):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=60)
        print(f"✅ Connected (attempt {attempt + 1})")
        break
    except Exception as e:
        print(f"⚠️  Attempt {attempt + 1} failed: {e}")
        if attempt < max_retries - 1:
            print("   Retrying in 30 seconds...")
            time.sleep(30)
        else:
            print("❌ Could not connect to server")
            exit(1)

try:
    # Kill any running builds
    print("\n🛑 Stopping any running builds...")
    stdin, stdout, stderr = client.exec_command(
        'pkill -f "pnpm build" || pkill -f "next build" || true'
    )
    stdout.channel.recv_exit_status()

    # Create remote directory if needed
    print("\n📁 Preparing remote directory...")
    stdin, stdout, stderr = client.exec_command(f"mkdir -p {REMOTE_DIR}/out")
    stdout.channel.recv_exit_status()

    # Clear existing out directory
    print("🧹 Clearing old build...")
    stdin, stdout, stderr = client.exec_command(f"rm -rf {REMOTE_DIR}/out/*")
    stdout.channel.recv_exit_status()

    # Upload files using SFTP
    print(f"\n📤 Uploading static files from {LOCAL_OUT_DIR}...")
    sftp = client.open_sftp()

    def upload_dir(local_dir, remote_dir):
        for item in os.listdir(local_dir):
            local_path = os.path.join(local_dir, item)
            remote_path = os.path.join(remote_dir, item).replace("\\", "/")

            if os.path.isfile(local_path):
                print(f"   📄 {item}")
                sftp.put(local_path, remote_path)
            elif os.path.isdir(local_path):
                try:
                    sftp.mkdir(remote_path)
                except:
                    pass  # Directory might exist
                upload_dir(local_path, remote_path)

    upload_dir(LOCAL_OUT_DIR, f"{REMOTE_DIR}/out")
    sftp.close()
    print("✅ Upload complete!")

    # Verify upload
    print("\n🔍 Verifying upload...")
    stdin, stdout, stderr = client.exec_command(f"ls -lah {REMOTE_DIR}/out/ | head -20")
    print(stdout.read().decode())

    # Configure Nginx
    print("\n⚙️ Configuring Nginx...")
    nginx_config = """server {
    listen 80;
    server_name _;

    root /opt/free-intelligence/apps/aurity/out;
    index index.html;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    location /api/ {
        proxy_pass http://localhost:7001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        try_files $uri $uri/ $uri.html /index.html;
    }
}"""

    stdin, stdout, stderr = client.exec_command(
        f"echo '{nginx_config}' > /etc/nginx/sites-available/aurity"
    )
    stdout.channel.recv_exit_status()

    # Enable site
    stdin, stdout, stderr = client.exec_command(
        """
        ln -sf /etc/nginx/sites-available/aurity /etc/nginx/sites-enabled/aurity
        rm -f /etc/nginx/sites-enabled/default
        nginx -t && systemctl reload nginx
    """
    )
    exit_code = stdout.channel.recv_exit_status()

    if exit_code == 0:
        print("✅ Nginx configured and reloaded!")
    else:
        print("❌ Nginx config failed!")
        print(stderr.read().decode())

    # Test deployment
    print("\n🧪 Testing deployment...")
    time.sleep(2)

    stdin, stdout, stderr = client.exec_command(
        "curl -s -o /dev/null -w '%{http_code}' http://localhost/"
    )
    http_code = stdout.read().decode().strip()

    print(f"   HTTP Status: {http_code}")

    if "200" in http_code:
        print("\n╔════════════════════════════════════════════╗")
        print("║      🎉 DEPLOYMENT SUCCESSFUL!             ║")
        print("╚════════════════════════════════════════════╝")
        print()
        print(f"🌐 Frontend live at: http://{HOST}/")
        print()

        # Get HTML preview
        stdin, stdout, stderr = client.exec_command("curl -s http://localhost/ | head -50")
        preview = stdout.read().decode()
        print("📄 Landing page preview:")
        print("=" * 60)
        print(preview)
        print("=" * 60)
    else:
        print(f"❌ Deployment failed! HTTP {http_code}")

finally:
    client.close()
