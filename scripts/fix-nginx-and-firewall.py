#!/usr/bin/env python3
"""Fix Nginx listening and UFW firewall"""
import paramiko
import time

HOST = '104.131.175.65'
USER = 'root'
PASSWORD = 'FreeIntel2024DO!'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)
    print("✅ Connected\n")

    # Check current nginx config
    print("📋 Current Nginx config:")
    stdin, stdout, stderr = client.exec_command('cat /etc/nginx/sites-enabled/aurity')
    current_config = stdout.read().decode()
    print(current_config)

    # Create correct Nginx config with explicit 0.0.0.0:80
    print("\n🔧 Creating new Nginx config with 0.0.0.0:80...")
    nginx_config = """server {
    listen 80;
    listen [::]:80;
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

    stdin, stdout, stderr = client.exec_command(f"cat > /etc/nginx/sites-enabled/aurity << 'EOF'\n{nginx_config}\nEOF")
    stdout.channel.recv_exit_status()
    print("✅ Config written")

    # Test config
    print("\n🧪 Testing Nginx config...")
    stdin, stdout, stderr = client.exec_command('nginx -t')
    test_output = stdout.read().decode() + stderr.read().decode()
    print(test_output)

    # Restart Nginx (not reload, full restart)
    print("\n🔄 Restarting Nginx...")
    stdin, stdout, stderr = client.exec_command('systemctl restart nginx')
    stdout.channel.recv_exit_status()
    time.sleep(2)

    # Verify it's listening
    print("\n✅ Verifying port 80...")
    stdin, stdout, stderr = client.exec_command('netstat -tlnp | grep :80')
    listen_output = stdout.read().decode()
    print(listen_output if listen_output else "❌ Still not listening!")

    # Open firewall
    print("\n🔥 Opening UFW firewall for HTTP/HTTPS...")
    stdin, stdout, stderr = client.exec_command('ufw allow 80/tcp && ufw allow 443/tcp')
    print(stdout.read().decode())

    # Show new firewall status
    print("\n📊 Updated UFW status:")
    stdin, stdout, stderr = client.exec_command('ufw status | grep -E "80|443"')
    print(stdout.read().decode())

    # Test local access
    print("\n🧪 Testing local access...")
    stdin, stdout, stderr = client.exec_command('curl -I http://localhost/ 2>&1 | head -3')
    print(stdout.read().decode())

    print("\n✅ Done! Try accessing http://104.131.175.65/ now")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    client.close()
