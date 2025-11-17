#!/usr/bin/env python3
"""Setup HTTPS with Let's Encrypt for DuckDNS domain"""
import paramiko

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"
DOMAIN = "fi-aurity.duckdns.org"
EMAIL = "bernarduriza@gmail.com"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)
    print("✅ Connected\n")

    # Install Certbot
    print("📦 Installing Certbot (Let's Encrypt client)...")
    commands = ["apt-get update -qq", "apt-get install -y -qq certbot python3-certbot-nginx"]

    for cmd in commands:
        print(f"   Running: {cmd}")
        stdin, stdout, stderr = client.exec_command(cmd)
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            print(f"   Error: {stderr.read().decode()}")
        else:
            print("   ✅ Done")

    # Update Nginx configuration for the domain
    print(f"\n🔧 Configuring Nginx for {DOMAIN}...")
    nginx_config = f"""server {{
    listen 80;
    server_name {DOMAIN};

    root /opt/free-intelligence/apps/aurity/out;
    index index.html;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    location /api/ {{
        proxy_pass http://localhost:7001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}

    location / {{
        try_files $uri $uri/ $uri.html /index.html;
    }}
}}"""

    # Write config
    stdin, stdout, stderr = client.exec_command(
        f"cat > /etc/nginx/sites-available/aurity << 'EOF'\n{nginx_config}\nEOF"
    )
    stdout.channel.recv_exit_status()

    # Enable site and reload
    stdin, stdout, stderr = client.exec_command(
        """
        ln -sf /etc/nginx/sites-available/aurity /etc/nginx/sites-enabled/aurity
        nginx -t && systemctl reload nginx
        """
    )
    if stdout.channel.recv_exit_status() == 0:
        print("✅ Nginx configured\n")
    else:
        print(f"❌ Nginx config error: {stderr.read().decode()}\n")
        raise Exception("Nginx configuration failed")

    # Test HTTP access
    print(f"🧪 Testing HTTP access to {DOMAIN}...")
    stdin, stdout, stderr = client.exec_command(
        f'curl -s -o /dev/null -w "%{{http_code}}" http://{DOMAIN}/'
    )
    http_code = stdout.read().decode().strip()
    if http_code == "200":
        print(f"✅ HTTP working (status: {http_code})\n")
    else:
        print(f"⚠️  HTTP returned {http_code}\n")

    # Get Let's Encrypt certificate
    print("🔒 Obtaining SSL certificate from Let's Encrypt...")
    print("   (This may take 30-60 seconds...)\n")

    certbot_cmd = (
        f"""certbot --nginx -d {DOMAIN} --non-interactive --agree-tos --email {EMAIL} --redirect"""
    )

    stdin, stdout, stderr = client.exec_command(certbot_cmd, get_pty=True)

    # Read output in real-time
    while True:
        line = stdout.readline()
        if not line:
            break
        print(f"   {line.strip()}")

    exit_code = stdout.channel.recv_exit_status()

    if exit_code == 0:
        print("\n✅ SSL certificate obtained and installed!\n")
    else:
        error = stderr.read().decode()
        print(f"\n❌ Certbot failed: {error}\n")
        raise Exception("SSL certificate setup failed")

    # Verify HTTPS is working
    print("🧪 Testing HTTPS...")
    stdin, stdout, stderr = client.exec_command(
        f'curl -s -o /dev/null -w "%{{http_code}}" https://{DOMAIN}/'
    )
    https_code = stdout.read().decode().strip()

    if https_code == "200":
        print(f"✅ HTTPS working! (status: {https_code})\n")
    else:
        print(f"⚠️  HTTPS returned {https_code}\n")

    # Check certificate details
    print("📋 Certificate details:")
    stdin, stdout, stderr = client.exec_command(f"certbot certificates -d {DOMAIN}")
    print(stdout.read().decode())

    print("\n╔════════════════════════════════════════════╗")
    print("║      ✅ HTTPS SETUP COMPLETE!             ║")
    print("╚════════════════════════════════════════════╝")
    print(f"\n🌐 Your site is now available at: https://{DOMAIN}/")
    print("🔒 SSL certificate will auto-renew via cron")
    print("\n📝 Next step: Update frontend to use HTTPS URL")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
finally:
    client.close()
