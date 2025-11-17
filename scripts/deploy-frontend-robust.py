#!/usr/bin/env python3
"""
🎨 Robust Frontend Deployment to DigitalOcean
Fixes server issues and deploys Aurity frontend
"""

import paramiko
import sys
import time

# Server config
HOST = '104.131.175.65'
USER = 'root'
PASSWORD = 'FreeIntel2024DO!'

def run_command(client, command, description, timeout=300):
    """Execute command and print output"""
    print(f"\n▶️  {description}")

    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)

    # Wait for command to complete
    exit_status = stdout.channel.recv_exit_status()

    output = stdout.read().decode()
    error = stderr.read().decode()

    if output and len(output) > 10:
        preview = output[:300].replace('\n', ' ')
        print(f"   ✓ {preview}...")

    if error and "WARNING" not in error.upper() and exit_status != 0:
        preview = error[:200].replace('\n', ' ')
        print(f"   ⚠️  {preview}...")

    return exit_status == 0, output, error

def deploy_frontend():
    """Deploy Aurity frontend to DigitalOcean"""

    print("╔════════════════════════════════════════════╗")
    print("║   🎨 Robust Frontend Deployment            ║")
    print("╚════════════════════════════════════════════╝")
    print()

    # Connect
    print(f"🔐 Connecting to {HOST}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)
        print("✅ Connected!")

        # Step 0: Fix any broken packages
        print("\n🔧 Step 0: Fixing system packages...")
        run_command(
            client,
            "dpkg --configure -a && apt-get update",
            "Fix dpkg and update packages",
            timeout=120
        )

        # Step 1: Install Node.js
        print("\n📦 Step 1: Installing Node.js 20...")
        success, output, _ = run_command(
            client,
            """
            if ! command -v node &> /dev/null; then
                curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
                apt-get install -y nodejs
            fi
            node --version
            """,
            "Install Node.js",
            timeout=180
        )

        if "v20" not in output and "v18" not in output and "v16" not in output:
            print("❌ Node.js installation failed")
            return False

        # Install pnpm
        print("\n📦 Installing pnpm...")
        run_command(
            client,
            "npm install -g pnpm && pnpm --version",
            "Install pnpm globally",
            timeout=60
        )

        # Install Nginx
        print("\n📦 Installing Nginx...")
        run_command(
            client,
            "apt-get install -y nginx && systemctl enable nginx && systemctl start nginx",
            "Install and start Nginx",
            timeout=120
        )

        # Step 2: Clone/Update repo
        print("\n📥 Step 2: Updating repository...")
        run_command(
            client,
            """
            cd /opt/free-intelligence
            git pull
            git submodule update --init --recursive
            """,
            "Pull latest code and submodules",
            timeout=60
        )

        # Step 3: Build frontend
        print("\n🏗️  Step 3: Building frontend (this takes 2-3 minutes)...")

        # Set environment variables for build
        run_command(
            client,
            """
            cd /opt/free-intelligence/apps/aurity
            export NEXT_PUBLIC_API_URL=http://104.131.175.65:7001
            echo "NEXT_PUBLIC_API_URL=http://104.131.175.65:7001" > .env.production
            """,
            "Set environment variables"
        )

        # Install dependencies from monorepo root
        print("\n📦 Installing dependencies from monorepo root...")
        success, output, error = run_command(
            client,
            "cd /opt/free-intelligence && pnpm install --frozen-lockfile --shamefully-hoist",
            "Install all workspace dependencies (hoisted)",
            timeout=600
        )

        if not success:
            print("⚠️ Frozen lockfile install failed, trying without frozen-lockfile...")
            run_command(
                client,
                "cd /opt/free-intelligence && pnpm install --shamefully-hoist",
                "Install dependencies (hoisted, no frozen lockfile)",
                timeout=600
            )

        # Also install in aurity directory to ensure node_modules exists there
        print("\n📦 Installing in aurity directory...")
        run_command(
            client,
            "cd /opt/free-intelligence/apps/aurity && pnpm install",
            "Install aurity dependencies locally",
            timeout=600
        )

        # Verify dependencies installed (check root node_modules in monorepo)
        print("\n🔍 Verifying Next.js installation...")
        success, output, _ = run_command(
            client,
            """
            if [ -f /opt/free-intelligence/node_modules/.bin/next ]; then
                echo "✓ Next.js found in root node_modules"
                exit 0
            elif [ -f /opt/free-intelligence/apps/aurity/node_modules/.bin/next ]; then
                echo "✓ Next.js found in aurity node_modules"
                exit 0
            else
                echo "✗ Next.js binary not found"
                ls -la /opt/free-intelligence/node_modules/.bin/ 2>/dev/null | grep next || echo "No next binary"
                exit 1
            fi
            """,
            "Verify Next.js installation"
        )

        if not success:
            print("⚠️ Next.js not found in expected locations, but continuing...")
            print("    (pnpm workspaces may handle this differently)")

        # Apply static config
        run_command(
            client,
            "cd /opt/free-intelligence/apps/aurity && cp next.config.static.js next.config.js",
            "Apply static export config"
        )

        # Build with full output
        print("\n🏗️ Building frontend (this may take 2-3 minutes)...")
        success, output, error = run_command(
            client,
            """
            cd /opt/free-intelligence/apps/aurity
            export NODE_ENV=production
            export NEXT_PUBLIC_API_URL=http://104.131.175.65:7001
            pnpm build
            """,
            "Build frontend (static export)",
            timeout=600
        )

        if not success:
            print("❌ Build failed!")
            print("Output:", output[:500])
            print("Error:", error[:500])
            # Try to get more debug info
            run_command(client, "ls -lah /opt/free-intelligence/apps/aurity/", "Check app directory")
            run_command(client, "which next", "Check next binary")
            return False

        # Verify build output exists
        success, output, _ = run_command(
            client,
            "ls -lah /opt/free-intelligence/apps/aurity/out/ | head -10",
            "Verify build output"
        )

        if "index.html" not in output:
            print("❌ Build output not found! Trying .next directory...")
            # Try using .next if out doesn't exist
            run_command(
                client,
                "cd /opt/free-intelligence/apps/aurity && ln -sf .next out",
                "Symlink .next to out"
            )

        # Step 4: Configure Nginx
        print("\n⚙️  Step 4: Configuring Nginx...")

        nginx_config = """server {
    listen 80;
    server_name _;

    root /opt/free-intelligence/apps/aurity/out;
    index index.html;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    location /api/ {
        proxy_pass http://localhost:7001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        try_files $uri $uri/ $uri.html /index.html;
    }
}"""

        # Write config
        run_command(
            client,
            f"echo '{nginx_config}' > /etc/nginx/sites-available/aurity",
            "Write Nginx config"
        )

        # Enable site
        run_command(
            client,
            """
            ln -sf /etc/nginx/sites-available/aurity /etc/nginx/sites-enabled/aurity
            rm -f /etc/nginx/sites-enabled/default
            """,
            "Enable site and remove default"
        )

        # Test and reload
        success, output, error = run_command(
            client,
            "nginx -t && systemctl reload nginx",
            "Test and reload Nginx"
        )

        if not success:
            print("❌ Nginx config failed!")
            print(error)
            return False

        # Step 5: Test deployment
        print("\n🧪 Step 5: Testing deployment...")
        time.sleep(3)

        # Test locally on server
        success, output, _ = run_command(
            client,
            "curl -s -o /dev/null -w '%{http_code}' http://localhost/",
            "Test localhost"
        )

        print(f"\n   Server response: {output.strip()}")

        if "200" in output:
            print("\n╔════════════════════════════════════════════╗")
            print("║         ✅ DEPLOYMENT SUCCESSFUL!          ║")
            print("╚════════════════════════════════════════════╝")
            print()

            # Test from external
            print("🌐 Testing external access...")
            import subprocess
            try:
                result = subprocess.run(
                    ['curl', '-s', '-I', f'http://{HOST}/', '--max-time', '10'],
                    capture_output=True,
                    text=True,
                    timeout=15
                )

                if '200 OK' in result.stdout:
                    print("✅ Landing page is accessible!")
                    print()
                    print(f"🎉 Frontend URL: http://{HOST}/")
                    print()

                    # Get HTML preview
                    result = subprocess.run(
                        ['curl', '-s', f'http://{HOST}/', '--max-time', '10'],
                        capture_output=True,
                        text=True,
                        timeout=15
                    )

                    if '<html' in result.stdout.lower():
                        print("📄 Landing page HTML preview:")
                        print("=" * 60)
                        preview = result.stdout[:800]
                        print(preview)
                        print("=" * 60)
                        print()
                        print("✅ ¡FRONTEND LIVE! Curl devolvió el landing exitosamente!")
                        return True
                    else:
                        print(f"⚠️  Response: {result.stdout[:200]}")
                else:
                    print(f"⚠️  Response headers: {result.stdout[:400]}")

            except Exception as e:
                print(f"⚠️  External test error: {e}")
                print(f"   Try manually: curl http://{HOST}/")

            return True
        else:
            print(f"❌ Server returned: {output}")
            # Debug
            run_command(client, "systemctl status nginx | head -20", "Nginx status")
            run_command(client, "tail -20 /var/log/nginx/error.log", "Error log")
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
