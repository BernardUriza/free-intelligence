#!/usr/bin/env python3
"""
🎨 Frontend Deployment to DigitalOcean using Paramiko
Deploys Aurity frontend to Droplet + Nginx
"""

import sys
import time

import paramiko

# Server config
HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"


def run_command(client, command, description):
    """Execute command and print output"""
    print(f"\n▶️  {description}")
    print(f"   Command: {command[:80]}...")

    stdin, stdout, stderr = client.exec_command(command)

    # Wait for command to complete
    exit_status = stdout.channel.recv_exit_status()

    output = stdout.read().decode()
    error = stderr.read().decode()

    if output:
        print(f"   ✓ {output[:200]}")

    if error and "WARNING" not in error and exit_status != 0:
        print(f"   ⚠️  {error[:200]}")

    return exit_status == 0, output, error


def deploy_frontend():
    """Deploy Aurity frontend to DigitalOcean"""

    print("╔════════════════════════════════════════════╗")
    print("║   🎨 Frontend Deployment to DigitalOcean   ║")
    print("╚════════════════════════════════════════════╝")
    print()

    # Connect
    print(f"🔐 Connecting to {HOST}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False)
        print("✅ Connected!")

        # Step 1: Install Node.js if not present
        print("\n📦 Step 1: Installing dependencies...")
        success, output, _ = run_command(
            client,
            "node --version || (curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs)",
            "Check/Install Node.js 20",
        )

        # Install pnpm
        run_command(client, "command -v pnpm || npm install -g pnpm", "Check/Install pnpm")

        # Install Nginx
        run_command(client, "command -v nginx || apt-get install -y nginx", "Check/Install Nginx")

        # Step 2: Clone/Update repo
        print("\n📥 Step 2: Cloning/Updating repository...")
        run_command(
            client,
            """
            if [ -d /opt/free-intelligence ]; then
                cd /opt/free-intelligence && git pull
            else
                git clone https://github.com/BernardUriza/free-intelligence.git /opt/free-intelligence
            fi
            """,
            "Clone/Pull repository",
        )

        # Update submodules
        run_command(
            client,
            "cd /opt/free-intelligence && git submodule update --init --recursive",
            "Update submodules (aurity)",
        )

        # Step 3: Build frontend
        print("\n🏗️  Step 3: Building frontend...")
        run_command(
            client,
            "cd /opt/free-intelligence/apps/aurity && pnpm install --no-frozen-lockfile",
            "Install frontend dependencies",
        )

        # Use static config for build
        run_command(
            client,
            "cd /opt/free-intelligence/apps/aurity && cp next.config.static.js next.config.js",
            "Apply static export config",
        )

        run_command(
            client,
            "cd /opt/free-intelligence/apps/aurity && pnpm build",
            "Build frontend (this may take 2-3 minutes)",
        )

        # Step 4: Configure Nginx
        print("\n⚙️  Step 4: Configuring Nginx...")

        nginx_config = """
server {
    listen 80;
    listen [::]:80;
    server_name _;

    root /opt/free-intelligence/apps/aurity/out;
    index index.html;

    # Enable gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 256;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # API proxy to backend
    location /api/ {
        proxy_pass http://localhost:7001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_cache_bypass $http_upgrade;
    }

    # Next.js static assets
    location /_next/static/ {
        alias /opt/free-intelligence/apps/aurity/out/_next/static/;
        expires 1y;
        access_log off;
        add_header Cache-Control "public, immutable";
    }

    # Images and other static files
    location ~* \\.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        access_log off;
        add_header Cache-Control "public";
    }

    # Client-side routing (SPA)
    location / {
        try_files $uri $uri/ $uri.html /index.html;
    }
}
"""

        # Write Nginx config
        run_command(
            client,
            f"cat > /etc/nginx/sites-available/aurity << 'EOF'\n{nginx_config}\nEOF",
            "Create Nginx config",
        )

        # Enable site
        run_command(
            client,
            "ln -sf /etc/nginx/sites-available/aurity /etc/nginx/sites-enabled/aurity",
            "Enable site",
        )

        # Remove default site
        run_command(client, "rm -f /etc/nginx/sites-enabled/default", "Remove default site")

        # Test Nginx config
        success, output, error = run_command(client, "nginx -t", "Test Nginx configuration")

        if not success:
            print("❌ Nginx config test failed!")
            print(error)
            return False

        # Reload Nginx
        run_command(client, "systemctl reload nginx", "Reload Nginx")

        # Step 5: Test deployment
        print("\n🧪 Step 5: Testing deployment...")

        # Wait a bit for Nginx to reload
        time.sleep(2)

        # Test locally
        success, output, _ = run_command(
            client,
            "curl -s -o /dev/null -w '%{http_code}' http://localhost/",
            "Test landing page (local)",
        )

        if "200" in output:
            print("\n╔════════════════════════════════════════════╗")
            print("║         ✅ DEPLOYMENT SUCCESSFUL!          ║")
            print("╚════════════════════════════════════════════╝")
            print()
            print("🌐 Your frontend is live at:")
            print(f"   http://{HOST}")
            print()
            print("📋 Testing from outside the server...")

            # Now test from local machine
            import subprocess

            try:
                result = subprocess.run(
                    ["curl", "-s", "-I", f"http://{HOST}/"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if "200 OK" in result.stdout:
                    print("✅ Landing page accessible from outside!")
                    print("\n🎉 Frontend deployed successfully!")
                    print(f"   URL: http://{HOST}")

                    # Get preview
                    print("\n📄 Landing page preview:")
                    result = subprocess.run(
                        ["curl", "-s", f"http://{HOST}/", "--max-time", "5"],
                        capture_output=True,
                        text=True,
                    )
                    preview = result.stdout[:500]
                    print(f"   {preview}...")

                else:
                    print("⚠️  Server responded but not with 200 OK")
                    print(result.stdout)

            except subprocess.TimeoutExpired:
                print("⏱️  Curl timeout - server might be slow")
            except Exception as e:
                print(f"⚠️  Could not test from local: {e}")
                print(f"   But server reports success. Try: curl http://{HOST}")

            return True
        else:
            print(f"❌ Landing page returned: {output}")

            # Debug
            print("\n🔍 Debugging...")
            run_command(
                client, "ls -lah /opt/free-intelligence/apps/aurity/out/", "Check build output"
            )
            run_command(client, "systemctl status nginx | head -20", "Nginx status")
            run_command(client, "tail -20 /var/log/nginx/error.log", "Nginx error log")

            return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        client.close()


if __name__ == "__main__":
    success = deploy_frontend()
    sys.exit(0 if success else 1)
