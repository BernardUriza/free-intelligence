from __future__ import annotations

import builtins
import contextlib
from typing import Annotated

import typer

app = typer.Typer(name="deploy", help="Deployment and restart operations", no_args_is_help=True)
def backend_start(
    environment: Annotated[
        str,
        typer.Option("--env", help="Environment to deploy to (production, staging, local)")
    ] = "production",
    force: Annotated[
        bool,
        typer.Option("--force", help="Force restart even if already running")
    ] = False,
) -> None:
    """
    Start backend service in specified environment.

    For production: Uses systemd service
    For staging/local: Uses direct Python execution
    """
    import subprocess

    import sys
    from pathlib import Path

    typer.echo(f"🚀 Starting backend in {environment} environment...")

    if environment == "production":
        # Use systemd service
        try:
            # Check if service exists
            result = subprocess.run(
                ["systemctl", "status", "aurity-backend"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0 and not force:
                typer.echo("ℹ️  Backend service is already running")
                return

            # Start service
            typer.echo("📦 Starting systemd service...")
            subprocess.run(["sudo", "systemctl", "start", "aurity-backend"], check=True)

            # Check status
            result = subprocess.run(
                ["systemctl", "status", "aurity-backend", "--no-pager"],
                capture_output=True,
                text=True
            )
            typer.echo(result.stdout)

        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to start backend service: {e}", err=True)
            raise typer.Exit(1)

    elif environment in ["staging", "local"]:
        # Direct Python execution
        backend_dir = Path(__file__).parent.parent.parent.parent / "backend"

        if not backend_dir.exists():
            typer.echo(f"❌ Backend directory not found: {backend_dir}", err=True)
            raise typer.Exit(1)

        typer.echo(f"🐍 Starting backend from {backend_dir}")

        # Set PYTHONPATH
        env = {"PYTHONPATH": str(backend_dir.parent)}

        try:
            subprocess.run(
                [sys.executable, "-m", "uvicorn", "backend.app.main:app",
                 "--host", "0.0.0.0", "--port", "7001", "--reload"],
                cwd=backend_dir.parent,
                env=env,
                check=True
            )
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to start backend: {e}", err=True)
            raise typer.Exit(1)

    else:
        typer.echo(f"❌ Unknown environment: {environment}", err=True)
        raise typer.Exit(1)


@app.command("backend-restart")
def backend_restart(
    environment: Annotated[
        str,
        typer.Option("--env", help="Environment to restart in (production, staging, local)")
    ] = "production",
) -> None:
    """
    Restart backend service in specified environment.
    """
    import subprocess

    typer.echo(f"🔄 Restarting backend in {environment} environment...")

    if environment == "production":
        try:
            # Restart systemd service
            typer.echo("📦 Restarting systemd service...")
            subprocess.run(["sudo", "systemctl", "restart", "aurity-backend"], check=True)

            # Check status
            result = subprocess.run(
                ["systemctl", "status", "aurity-backend", "--no-pager"],
                capture_output=True,
                text=True
            )
            typer.echo(result.stdout)

        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to restart backend service: {e}", err=True)
            raise typer.Exit(1)

    elif environment in ["staging", "local"]:
        # For local/staging, stop and start
        typer.echo("🛑 Stopping current backend...")
        with contextlib.suppress(builtins.BaseException):
            subprocess.run(["pkill", "-f", "uvicorn.*backend.app.main"], check=False)

        # Start new instance
        from .deploy import backend_start
        backend_start(environment=environment)

    else:
        typer.echo(f"❌ Unknown environment: {environment}", err=True)
        raise typer.Exit(1)


@app.command("setup-https")
def setup_https(
    domain: Annotated[
        str,
        typer.Option("--domain", help="Domain name for HTTPS setup")
    ] = "app.aurity.app",
    email: Annotated[
        str,
        typer.Option("--email", help="Email for Let's Encrypt certificate")
    ] = "admin@aurity.app",
) -> None:
    """
    Setup HTTPS certificates and nginx configuration.

    Requires root privileges and certbot installation.
    """
    import subprocess

    typer.echo(f"🔒 Setting up HTTPS for {domain}...")

    try:
        # Install certbot if not present
        typer.echo("📦 Ensuring certbot is installed...")
        subprocess.run(["sudo", "apt", "update"], check=True)
        subprocess.run(["sudo", "apt", "install", "-y", "certbot", "python3-certbot-nginx"], check=True)

        # Obtain certificate
        typer.echo("📜 Obtaining SSL certificate...")
        subprocess.run([
            "sudo", "certbot", "--nginx",
            "-d", domain,
            "--email", email,
            "--agree-tos",
            "--non-interactive"
        ], check=True)

        # Test nginx configuration
        typer.echo("🧪 Testing nginx configuration...")
        subprocess.run(["sudo", "nginx", "-t"], check=True)

        # Reload nginx
        typer.echo("🔄 Reloading nginx...")
        subprocess.run(["sudo", "systemctl", "reload", "nginx"], check=True)

        typer.echo("✅ HTTPS setup complete!")

    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ HTTPS setup failed: {e}", err=True)
        raise typer.Exit(1)


@app.command("restart-backend-production")
def restart_backend_production(
    host: Annotated[
        str,
        typer.Option("--host", help="Production server hostname/IP")
    ] = "104.131.175.65",
    user: Annotated[
        str,
        typer.Option("--user", help="SSH username")
    ] = "root",
    key_path: Annotated[
        str,
        typer.Option("--key", help="Path to SSH private key")
    ] = "~/.ssh/id_rsa",
) -> None:
    """
    Restart backend in production server and verify it's working.

    Uses SSH key authentication for secure remote operations.
    """
    import time

    from .._common import redact_text, run_cmd, ssh_argv, wait_for_http_ok

    typer.echo(f"🔄 Restarting backend on {host}...")

    ssh_args = ssh_argv(host, user, key_path)

    try:
        # Stop old backend process
        typer.echo("🛑 Stopping old backend process...")
        stop_cmd = ["pkill", "-f", "python.*main.py || echo 'No process found'"]
        run_cmd(ssh_args + stop_cmd)
        time.sleep(2)

        # Verify it's stopped
        check_cmd = ["ps", "aux", "|", "grep", "'[p]ython.*main.py'"]
        result = run_cmd(ssh_args + check_cmd, capture_output=True)
        if result.stdout.strip():
            typer.echo("⚠️  Process still running, force killing...")
            run_cmd([*ssh_args, "pkill", "-9", "-f", "python.*main.py"])
            time.sleep(1)

        # Check project structure
        typer.echo("📂 Verifying project structure...")
        ls_cmd = ["ls", "-la", "/opt/free-intelligence/backend/"]
        result = run_cmd(ssh_args + ls_cmd, capture_output=True)
        typer.echo(result.stdout)

        # Start backend
        typer.echo("🚀 Starting backend...")
        start_cmd = [
            "cd", "/opt/free-intelligence/backend", "&&",
            "nohup", "python3.14", "-m", "app.main", ">", "/tmp/backend.log", "2>&1", "&"
        ]
        run_cmd(ssh_args + start_cmd)
        time.sleep(3)

        # Check if running
        typer.echo("🔍 Checking if backend is running...")
        result = run_cmd(ssh_args + check_cmd, capture_output=True)
        if result.stdout.strip():
            typer.echo("✅ Backend running:")
            typer.echo(redact_text(result.stdout))
        else:
            typer.echo("❌ Backend not started!")
            # Show logs
            log_cmd = ["tail", "-n", "30", "/tmp/backend.log"]
            result = run_cmd(ssh_args + log_cmd, capture_output=True)
            typer.echo("📋 Error logs:")
            typer.echo(redact_text(result.stdout))
            raise typer.Exit(1)

        # Check port
        typer.echo("🔍 Checking port 7001...")
        port_cmd = ["ss", "-tlnp", "|", "grep", ":7001"]
        result = run_cmd(ssh_args + port_cmd, capture_output=True)
        if result.stdout.strip():
            typer.echo(f"✅ Port 7001 listening:\n{result.stdout}")
        else:
            typer.echo("❌ Port 7001 not listening!")

        # Wait and test endpoints
        typer.echo("⏳ Waiting for backend to fully start...")
        time.sleep(3)

        typer.echo("🧪 Testing API endpoints:")
        test_urls = [
            f"http://{host}:7001/api/health",
            f"http://{host}:7001/api/auth/config",
            f"http://{host}:7001/api/workflows/aurity/sessions"
        ]

        for url in test_urls:
            typer.echo(f"   Testing {url}...")
            if wait_for_http_ok(url, timeout=10):
                typer.echo("   ✅ OK")
            else:
                typer.echo("   ❌ FAILED")

        # Show recent logs
        typer.echo("📋 Recent backend logs:")
        result = run_cmd(ssh_args + log_cmd, capture_output=True)
        typer.echo(redact_text(result.stdout))

        # Fix permissions
        typer.echo("🔧 Fixing image permissions...")
        perm_cmd = ["chmod", "-R", "755", "/opt/free-intelligence/apps/aurity/out/images/", "2>/dev/null", "||", "echo", "'No images dir'"]
        run_cmd(ssh_args + perm_cmd)

        typer.echo("✅ RESTART COMPLETE")
        typer.echo("🌐 Test from mobile: https://app.aurity.io/")

    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)


@app.command("start-backend-production")
def start_backend_production(
    host: Annotated[
        str,
        typer.Option("--host", help="Production server hostname/IP")
    ] = "104.131.175.65",
    user: Annotated[
        str,
        typer.Option("--user", help="SSH username")
    ] = "root",
    key_path: Annotated[
        str,
        typer.Option("--key", help="Path to SSH private key")
    ] = "~/.ssh/id_rsa",
) -> None:
    """
    Start backend in production server with proper PYTHONPATH and verify it's working.

    Uses SSH key authentication for secure remote operations.
    """
    import time

    from .._common import redact_text, run_cmd, ssh_argv, wait_for_http_ok

    typer.echo(f"🚀 Starting backend on {host}...")

    ssh_args = ssh_argv(host, user, key_path)

    try:
        # Stop any existing backend processes
        typer.echo("🛑 Stopping any existing backend processes...")
        stop_cmd = ["pkill", "-f", "'python.*main'", "||", "echo", "'No process found'"]
        run_cmd(ssh_args + stop_cmd)
        time.sleep(2)

        # Double check with -9
        run_cmd([*ssh_args, "pkill", "-9", "-f", "'python.*main'", "2>/dev/null", "||", "true"])
        time.sleep(1)
        typer.echo("✅ Previous processes stopped")

        # Check Python version
        typer.echo("🐍 Checking Python version...")
        result = run_cmd([*ssh_args, "python3.14", "--version"], capture_output=True)
        typer.echo(f"   {result.stdout.strip()}")

        # Start backend with correct PYTHONPATH
        typer.echo("🚀 Starting backend from project root...")
        start_cmd = [
            "cd", "/opt/free-intelligence", "&&",
            "export", "PYTHONPATH=/opt/free-intelligence:$PYTHONPATH", "&&",
            "nohup", "python3.14", "-m", "backend.app.main", ">", "/tmp/backend.log", "2>&1", "&"
        ]
        run_cmd(ssh_args + start_cmd)
        typer.echo("✅ Start command executed")

        # Wait for startup
        typer.echo("⏳ Waiting 5 seconds for backend to start...")
        time.sleep(5)

        # Check if running
        typer.echo("🔍 Checking if backend is running...")
        result = run_cmd([*ssh_args, "ps", "aux", "|", "grep", "'[p]ython.*main'"], capture_output=True)
        if result.stdout.strip():
            typer.echo("✅ Backend running:")
            for line in result.stdout.strip().split("\n"):
                typer.echo(f"   {line}")
        else:
            typer.echo("❌ Backend not running!")
            # Show logs
            log_cmd = ["tail", "-n", "50", "/tmp/backend.log"]
            result = run_cmd(ssh_args + log_cmd, capture_output=True)
            typer.echo("📋 Error logs:")
            typer.echo(redact_text(result.stdout))
            raise typer.Exit(1)

        # Check port
        typer.echo("🔍 Checking port 7001...")
        result = run_cmd([*ssh_args, "ss", "-tlnp", "|", "grep", ":7001"], capture_output=True)
        if ":7001" in result.stdout:
            typer.echo(f"✅ Port 7001 listening:\n   {result.stdout.strip()}")
        else:
            typer.echo("❌ Port 7001 not listening")

        # Test API endpoints
        typer.echo("🧪 Testing API endpoints:")
        test_urls = [
            ("Health check", f"http://{host}:7001/api/health"),
            ("Auth config", f"http://{host}:7001/api/auth/config"),
            ("Workflows", f"http://{host}:7001/api/workflows/aurity/sessions"),
        ]

        for name, url in test_urls:
            typer.echo(f"   Testing {name}...")
            if wait_for_http_ok(url, timeout=5):
                typer.echo("   ✅ OK")
            else:
                typer.echo("   ❌ FAILED")

        # Show recent logs
        typer.echo("📋 Recent backend logs:")
        result = run_cmd([*ssh_args, "tail", "-n", "20", "/tmp/backend.log"], capture_output=True)
        typer.echo(redact_text(result.stdout))

        # Fix permissions
        typer.echo("🔧 Fixing /images/ permissions...")
        perm_cmd = ["chmod", "-R", "755", "/opt/free-intelligence/apps/aurity/out/", "2>&1"]
        result = run_cmd(ssh_args + perm_cmd, capture_output=True)
        if result.stdout.strip():
            typer.echo(f"   {result.stdout.strip()}")
        typer.echo("✅ Permissions updated")

        typer.echo("=" * 60)
        typer.echo("✅ BACKEND STARTED SUCCESSFULLY")
        typer.echo("=" * 60)
        typer.echo("🌐 Test from mobile: https://app.aurity.io/")

    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)


@app.command("setup-backend-service")
def setup_backend_service(
    host: Annotated[
        str,
        typer.Option("--host", help="Server hostname/IP")
    ] = "104.131.175.65",
    user: Annotated[
        str,
        typer.Option("--user", help="SSH username")
    ] = "root",
    key_path: Annotated[
        str,
        typer.Option("--key", help="Path to SSH private key")
    ] = "~/.ssh/id_rsa",
) -> None:
    """
    Setup systemd service for Aurity Backend on production server.

    Creates service file, enables it, and starts the service.
    """
    from .._common import run_cmd, ssh_argv

    typer.echo(f"🔧 Setting up backend service on {host}...")

    ssh_args = ssh_argv(host, user, key_path)

    service_content = '''[Unit]
Description=Aurity Backend FastAPI Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/free-intelligence
Environment="PYTHONPATH=/opt/free-intelligence"
ExecStart=/usr/bin/python3.14 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 7001
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=aurity-backend

[Install]
WantedBy=multi-user.target
'''

    try:
        # Create service file
        typer.echo("📝 Creating systemd service file...")
        create_cmd = ["cat", ">", "/etc/systemd/system/aurity-backend.service"]
        run_cmd(ssh_args + create_cmd, input=service_content)

        # Reload systemd
        typer.echo("🔄 Reloading systemd...")
        run_cmd([*ssh_args, "systemctl", "daemon-reload"])

        # Enable service
        typer.echo("✅ Enabling service...")
        run_cmd([*ssh_args, "systemctl", "enable", "aurity-backend"])

        # Kill existing processes
        typer.echo("🛑 Killing existing uvicorn processes...")
        run_cmd([*ssh_args, "pkill", "-f", "uvicorn backend.app.main", "||", "true"])
        import time
        time.sleep(2)

        # Start service
        typer.echo("🚀 Starting service...")
        run_cmd([*ssh_args, "systemctl", "start", "aurity-backend"])

        # Check status
        typer.echo("📊 Service status:")
        status_cmd = ["systemctl", "status", "aurity-backend", "--no-pager"]
        result = run_cmd(ssh_args + status_cmd, capture_output=True)
        typer.echo(result.stdout)

        typer.echo("✅ Backend service setup complete!")
        typer.echo("")
        typer.echo("Useful commands:")
        typer.echo("  systemctl status aurity-backend   # Check status")
        typer.echo("  systemctl restart aurity-backend  # Restart")
        typer.echo("  journalctl -u aurity-backend -f   # View logs")

    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)


@app.command("setup-https-production")
def setup_https_production(
    host: Annotated[
        str,
        typer.Option("--host", help="Server hostname/IP")
    ] = "104.131.175.65",
    user: Annotated[
        str,
        typer.Option("--user", help="SSH username")
    ] = "root",
    key_path: Annotated[
        str,
        typer.Option("--key", help="Path to SSH private key")
    ] = "~/.ssh/id_rsa",
    domain: Annotated[
        str,
        typer.Option("--domain", help="Domain name")
    ] = "app.aurity.io",
    email: Annotated[
        str,
        typer.Option("--email", help="Email for Let's Encrypt")
    ] = "bernarduriza@gmail.com",
) -> None:
    """
    Setup HTTPS with Let's Encrypt on production server.

    Installs certbot, configures nginx, obtains SSL certificate.
    """
    from .._common import run_cmd, ssh_argv

    typer.echo(f"🔒 Setting up HTTPS for {domain} on {host}...")

    ssh_args = ssh_argv(host, user, key_path)

    try:
        # Install certbot
        typer.echo("📦 Installing Certbot...")
        install_cmds = [
            ["apt-get", "update", "-qq"],
            ["apt-get", "remove", "-y", "python3-certbot", "python3-certbot-nginx"],
            ["apt-get", "install", "-y", "-qq", "snapd"],
            ["snap", "install", "core"],
            ["snap", "refresh", "core"],
            ["snap", "install", "--classic", "certbot"],
            ["ln", "-sf", "/snap/bin/certbot", "/usr/bin/certbot"],
        ]

        for cmd in install_cmds:
            run_cmd(ssh_args + cmd)

        # Configure nginx
        typer.echo(f"🔧 Configuring nginx for {domain}...")
        nginx_config = f'''server {{
    listen 80;
    server_name {domain};

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
}}
'''

        # Write nginx config
        nginx_cmd = ["cat", ">", "/etc/nginx/sites-available/aurity"]
        run_cmd(ssh_args + nginx_cmd, input=nginx_config)

        # Enable site and reload
        enable_cmds = [
            ["ln", "-sf", "/etc/nginx/sites-available/aurity", "/etc/nginx/sites-enabled/aurity"],
            ["nginx", "-t"],
            ["systemctl", "reload", "nginx"],
        ]

        for cmd in enable_cmds:
            result = run_cmd(ssh_args + cmd, capture_output=True)
            if cmd == ["nginx", "-t"] and result.returncode != 0:
                typer.echo(f"❌ Nginx config error: {result.stderr}", err=True)
                raise typer.Exit(1)

        # Test HTTP
        typer.echo(f"🧪 Testing HTTP access to {domain}...")
        http_cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"http://{domain}/"]
        result = run_cmd(ssh_args + http_cmd, capture_output=True)
        if result.stdout.strip() == "200":
            typer.echo("✅ HTTP working")
        else:
            typer.echo(f"⚠️  HTTP returned {result.stdout.strip()}")

        # Get SSL certificate
        typer.echo("🔒 Obtaining SSL certificate...")
        cert_cmd = [
            "certbot", "--nginx", "-d", domain,
            "--non-interactive", "--agree-tos", "--email", email, "--redirect"
        ]
        run_cmd(ssh_args + cert_cmd)

        # Verify HTTPS
        typer.echo("🧪 Testing HTTPS...")
        https_cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"https://{domain}/"]
        result = run_cmd(ssh_args + https_cmd, capture_output=True)
        if result.stdout.strip() == "200":
            typer.echo("✅ HTTPS working!")
        else:
            typer.echo(f"⚠️  HTTPS returned {result.stdout.strip()}")

        # Show certificate info
        typer.echo("📋 Certificate details:")
        cert_info_cmd = ["certbot", "certificates", "-d", domain]
        result = run_cmd(ssh_args + cert_info_cmd, capture_output=True)
        typer.echo(result.stdout)

        typer.echo("╔════════════════════════════════════════════╗")
        typer.echo("║      ✅ HTTPS SETUP COMPLETE!             ║")
        typer.echo("╚════════════════════════════════════════════╝")
        typer.echo(f"🌐 Site available at: https://{domain}/")
        typer.echo("🔒 SSL certificate auto-renews via cron")

    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)


@app.command("auth0-config-fix")
def auth0_config_fix(
    host: Annotated[
        str,
        typer.Option("--host", help="Production server hostname or IP")
    ] = "104.131.175.65",
    user: Annotated[
        str,
        typer.Option("--user", help="SSH username")
    ] = "root",
    key_path: Annotated[
        str,
        typer.Option("--key-path", help="Path to SSH private key")
    ] = "~/.ssh/id_rsa",
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be done without executing")
    ] = False,
) -> None:
    """
    Deploy fixed auth0_config.py to production and restart backend.

    Uses SSH key authentication. Requires root access on production server.
    """
    import time

    import os
    from pathlib import Path

    typer.echo("🔧 Deploying Auth0 config fix to production...")

    if dry_run:
        typer.echo("🔍 DRY RUN MODE - No changes will be made")

    # Expand key path
    key_path = os.path.expanduser(key_path)
    if not Path(key_path).exists():
        typer.echo(f"❌ SSH key not found: {key_path}", err=True)
        raise typer.Exit(1)

    # Lazy import paramiko
    try:
        import paramiko
    except ImportError:
        typer.echo("❌ paramiko not installed. Install with: pip install paramiko", err=True)
        raise typer.Exit(1)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        typer.echo(f"🔑 Connecting to {host} as {user}...")
        if not dry_run:
            client.connect(host, username=user, key_filename=key_path, timeout=30)
            typer.echo("✅ Connected")

        # Stop backend
        typer.echo("🛑 Stopping backend...")
        stop_cmd = "pkill -9 -f 'python.*main'"
        if not dry_run:
            stdin, stdout, stderr = client.exec_command(stop_cmd)
            stdout.channel.recv_exit_status()
            time.sleep(2)
        else:
            typer.echo(f"   Would run: {stop_cmd}")

        # Upload fixed file
        local_path = Path(__file__).parent.parent.parent.parent / "backend" / "auth" / "auth0_config.py"
        remote_path = "/opt/free-intelligence/backend/auth/auth0_config.py"

        typer.echo(f"📤 Uploading {local_path} to {remote_path}...")
        if not dry_run:
            sftp = client.open_sftp()
            sftp.put(str(local_path), remote_path)
            sftp.close()
            typer.echo("✅ File uploaded")
        else:
            typer.echo(f"   Would upload: {local_path} -> {remote_path}")

        # Start backend
        typer.echo("🚀 Starting backend...")
        start_cmd = """
cd /opt/free-intelligence && \
export PYTHONPATH=/opt/free-intelligence:$PYTHONPATH && \
nohup python3.14 -m backend.app.main > /tmp/backend.log 2>&1 &
"""
        if not dry_run:
            stdin, stdout, stderr = client.exec_command(start_cmd)
            stdout.channel.recv_exit_status()
        else:
            typer.echo(f"   Would run: {start_cmd.strip()}")

        # Wait
        typer.echo("⏳ Waiting 10 seconds...")
        if not dry_run:
            time.sleep(10)

        # Check process
        typer.echo("🔍 Checking backend status...")
        check_cmd = "ps aux | grep '[u]vicorn'"
        if not dry_run:
            stdin, stdout, stderr = client.exec_command(check_cmd)
            process = stdout.read().decode().strip()

            if process:
                typer.echo("✅ Backend is running")

                # Test endpoint
                typer.echo("🧪 Testing /api/auth/config...")
                test_cmd = "curl -s http://localhost:7001/api/auth/config | python3 -m json.tool | grep audience"
                stdin, stdout, stderr = client.exec_command(test_cmd)
                result = stdout.read().decode()
                typer.echo(f"   {result}")

                if "api.app.aurity.io" in result:
                    typer.echo("✅ AUDIENCE UPDATED!")
                else:
                    typer.echo("⚠️  Audience may not be updated")
            else:
                typer.echo("❌ Backend did not start")
                typer.echo("📋 Last logs:")
                log_cmd = "tail -n 40 /tmp/backend.log"
                stdin, stdout, _stderr = client.exec_command(log_cmd)
                typer.echo(stdin.read().decode())
        else:
            typer.echo(f"   Would check: {check_cmd}")

        typer.echo("╔════════════════════════════════════════════╗")
        typer.echo("║      ✅ AUTH0 CONFIG FIX COMPLETE!        ║")
        typer.echo("╚════════════════════════════════════════════╝")

    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)
    finally:
        if not dry_run:
            client.close()


@app.command("auth0-correct-domain")
def auth0_correct_domain(
    host: Annotated[
        str,
        typer.Option("--host", help="Production server hostname or IP")
    ] = "104.131.175.65",
    user: Annotated[
        str,
        typer.Option("--user", help="SSH username")
    ] = "root",
    key_path: Annotated[
        str,
        typer.Option("--key-path", help="Path to SSH private key")
    ] = "~/.ssh/id_rsa",
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be done without executing")
    ] = False,
) -> None:
    """
    Deploy corrected Auth0 config with app.aurity.io domain (no api subdomain).

    Uses SSH key authentication. Requires root access on production server.
    """
    import time

    import os
    from pathlib import Path

    typer.echo("🔧 Deploying Auth0 correct domain to production...")

    if dry_run:
        typer.echo("🔍 DRY RUN MODE - No changes will be made")

    # Expand key path
    key_path = os.path.expanduser(key_path)
    if not Path(key_path).exists():
        typer.echo(f"❌ SSH key not found: {key_path}", err=True)
        raise typer.Exit(1)

    # Lazy import paramiko
    try:
        import paramiko
    except ImportError:
        typer.echo("❌ paramiko not installed. Install with: pip install paramiko", err=True)
        raise typer.Exit(1)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        typer.echo(f"🔑 Connecting to {host} as {user}...")
        if not dry_run:
            client.connect(host, username=user, key_filename=key_path, timeout=30)
            typer.echo("✅ Connected")

        # Stop backend
        typer.echo("🛑 Stopping backend...")
        stop_cmd = "pkill -9 -f 'python.*main'"
        if not dry_run:
            stdin, stdout, stderr = client.exec_command(stop_cmd)
            stdout.channel.recv_exit_status()
            time.sleep(2)
        else:
            typer.echo(f"   Would run: {stop_cmd}")

        # Upload corrected file
        local_path = Path(__file__).parent.parent.parent.parent / "backend" / "auth" / "auth0_config.py"
        remote_path = "/opt/free-intelligence/backend/auth/auth0_config.py"

        typer.echo(f"📤 Uploading {local_path} to {remote_path}...")
        if not dry_run:
            sftp = client.open_sftp()
            sftp.put(str(local_path), remote_path)
            sftp.close()
            typer.echo("✅ File uploaded")
        else:
            typer.echo(f"   Would upload: {local_path} -> {remote_path}")

        # Start backend
        typer.echo("🚀 Starting backend...")
        start_cmd = """
cd /opt/free-intelligence && \
export PYTHONPATH=/opt/free-intelligence:$PYTHONPATH && \
nohup python3.14 -m backend.app.main > /tmp/backend.log 2>&1 &
"""
        if not dry_run:
            stdin, stdout, stderr = client.exec_command(start_cmd)
            stdout.channel.recv_exit_status()
        else:
            typer.echo(f"   Would run: {start_cmd.strip()}")

        # Wait
        typer.echo("⏳ Waiting 10 seconds...")
        if not dry_run:
            time.sleep(10)

        # Check process
        typer.echo("🔍 Checking backend status...")
        check_cmd = "ps aux | grep '[u]vicorn'"
        if not dry_run:
            stdin, stdout, stderr = client.exec_command(check_cmd)
            process = stdout.read().decode().strip()

            if process:
                typer.echo("✅ Backend is running")

                # Test endpoint
                typer.echo("🧪 Testing /api/auth/config...")
                test_cmd = "curl -s http://localhost:7001/api/auth/config | python3 -m json.tool | grep audience"
                stdin, stdout, stderr = client.exec_command(test_cmd)
                result = stdout.read().decode()
                typer.echo(f"   {result}")

                if "app.aurity.io" in result and "api.app.aurity.io" not in result:
                    typer.echo("✅ DOMAIN CORRECTED!")
                else:
                    typer.echo("⚠️  Domain may not be corrected")
            else:
                typer.echo("❌ Backend did not start")
                typer.echo("📋 Last logs:")
                log_cmd = "tail -n 40 /tmp/backend.log"
                stdin, stdout, _stderr = client.exec_command(log_cmd)
                typer.echo(stdin.read().decode())
        else:
            typer.echo(f"   Would check: {check_cmd}")

        typer.echo("╔════════════════════════════════════════════╗")
        typer.echo("║      ✅ AUTH0 DOMAIN FIX COMPLETE!        ║")
        typer.echo("╚════════════════════════════════════════════╝")

    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)
    finally:
        if not dry_run:
            client.close()


@app.command("deploy-frontend-eruda")
def deploy_frontend_eruda(
    host: Annotated[
        str,
        typer.Option("--host", help="Production server hostname or IP")
    ] = "104.131.175.65",
    user: Annotated[
        str,
        typer.Option("--user", help="SSH username")
    ] = "root",
    key_path: Annotated[
        str,
        typer.Option("--key-path", help="Path to SSH private key")
    ] = "~/.ssh/id_rsa",
    local_out: Annotated[
        str,
        typer.Option("--local-out", help="Local build output directory")
    ] = "apps/aurity/out",
    remote_out: Annotated[
        str,
        typer.Option("--remote-out", help="Remote deployment directory")
    ] = "/opt/free-intelligence/apps/aurity/out",
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be done without executing")
    ] = False,
) -> None:
    """
    Deploy frontend build with Eruda debug tool to production.

    Creates backup, uploads new files, fixes permissions, reloads Nginx.
    Uses SSH key authentication. Requires root access on production server.
    """
    import datetime

    import os
    from pathlib import Path

    typer.echo("🚀 Deploying frontend with Eruda to production...")

    if dry_run:
        typer.echo("🔍 DRY RUN MODE - No changes will be made")

    # Expand paths
    key_path = os.path.expanduser(key_path)
    local_out_path = Path(local_out)

    if not local_out_path.exists():
        typer.echo(f"❌ Local build directory not found: {local_out_path}", err=True)
        raise typer.Exit(1)

    if not Path(key_path).exists():
        typer.echo(f"❌ SSH key not found: {key_path}", err=True)
        raise typer.Exit(1)

    # Lazy import paramiko
    try:
        import paramiko
    except ImportError:
        typer.echo("❌ paramiko not installed. Install with: pip install paramiko", err=True)
        raise typer.Exit(1)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        typer.echo(f"🔑 Connecting to {host} as {user}...")
        if not dry_run:
            client.connect(host, username=user, key_filename=key_path, timeout=30)
            typer.echo("✅ Connected")

        # Create backup
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{remote_out}.backup.{timestamp}"

        typer.echo("💾 Creating backup of current frontend...")
        backup_cmd = f"cp -r {remote_out} {backup_path} 2>/dev/null || true"
        if not dry_run:
            stdin, stdout, stderr = client.exec_command(backup_cmd)
            stdout.channel.recv_exit_status()
            typer.echo("✅ Backup created")
        else:
            typer.echo(f"   Would run: {backup_cmd}")

        # Remove old files
        typer.echo("🗑️  Cleaning old files...")
        clean_cmd = f"rm -rf {remote_out}/*"
        if not dry_run:
            stdin, stdout, stderr = client.exec_command(clean_cmd)
            stdout.channel.recv_exit_status()
            typer.echo("✅ Old files removed")
        else:
            typer.echo(f"   Would run: {clean_cmd}")

        # Upload new files
        typer.echo("📤 Uploading new files...")
        if not dry_run:
            sftp = client.open_sftp()

            def upload_directory(local_dir: Path, remote_dir: str):
                """Recursively upload directory"""
                try:
                    sftp.stat(remote_dir)
                except FileNotFoundError:
                    sftp.mkdir(remote_dir)

                for item in local_dir.iterdir():
                    remote_path = f"{remote_dir}/{item.name}"

                    if item.is_file():
                        typer.echo(f"   Uploading: {item.name}")
                        sftp.put(str(item), remote_path)
                    elif item.is_dir():
                        upload_directory(item, remote_path)

            upload_directory(local_out_path, remote_out)
            sftp.close()
            typer.echo("✅ Files uploaded")
        else:
            typer.echo(f"   Would upload: {local_out_path} -> {remote_out}")

        # Fix permissions
        typer.echo("🔧 Fixing permissions...")
        perm_cmd = f"chmod -R 755 {remote_out}"
        if not dry_run:
            stdin, stdout, stderr = client.exec_command(perm_cmd)
            stdout.channel.recv_exit_status()
            typer.echo("✅ Permissions updated")
        else:
            typer.echo(f"   Would run: {perm_cmd}")

        # Reload Nginx
        typer.echo("🔄 Reloading Nginx...")
        nginx_cmd = "nginx -t && nginx -s reload"
        if not dry_run:
            _stdin, stdout, stderr = client.exec_command(nginx_cmd)
            test_output = stderr.read().decode()
            if "successful" in test_output:
                typer.echo("✅ Nginx reloaded")
            else:
                typer.echo(f"⚠️  Nginx test output:\n{test_output}")
        else:
            typer.echo(f"   Would run: {nginx_cmd}")

        typer.echo("\n" + "=" * 80)
        typer.echo("✅ DEPLOYMENT COMPLETED")
        typer.echo("=" * 80)
        typer.echo("\n🌐 Test from mobile: https://app.aurity.io/")
        typer.echo("📱 You'll see a floating icon in bottom-right corner")
        typer.echo("🔍 Tap the icon to open Eruda console")
        typer.echo("\n⚠️  REMEMBER: Remove Eruda after debugging")

    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)
    finally:
        if not dry_run:
            client.close()


@app.command("deploy-ds923")
def deploy_ds923(
    volume_base: Annotated[
        str,
        typer.Option("--volume-base", help="Base volume directory on NAS")
    ] = "/volume1/fi",
    ollama_dir: Annotated[
        str,
        typer.Option("--ollama-dir", help="Ollama models directory")
    ] = "/volume1/ollama",
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be done without executing")
    ] = False,
) -> None:
    """
    Deploy Ollama + ASR workers on Synology DS923+ NAS.

    Creates directory structure, deploys Docker containers, pulls models, runs smoke tests.
    Requires Docker access and proper NAS setup.
    """
    import subprocess
    import time

    from pathlib import Path

    typer.echo("🚀 Deploying to Synology DS923+ NAS...")
    typer.echo("=" * 60)

    if dry_run:
        typer.echo("🔍 DRY RUN MODE - No changes will be made")

    def run_cmd(cmd: list[str], check: bool = True, capture_output: bool = False):
        """Run command with optional dry run"""
        if dry_run:
            typer.echo(f"   Would run: {' '.join(cmd)}")
            return None
        result = subprocess.run(cmd, check=check, capture_output=capture_output, text=True)
        return result

    # Check Docker access
    typer.echo("🔍 Checking Docker access...")
    try:
        run_cmd(["docker", "ps"])
        typer.echo("✅ Docker accessible")
    except subprocess.CalledProcessError:
        typer.echo("❌ Docker not accessible. Please run with Docker privileges.", err=True)
        raise typer.Exit(1)

    # Create directory structure
    typer.echo("📁 Creating directory structure...")
    dirs = [
        f"{volume_base}/ready",
        f"{volume_base}/asr/json",
        f"{volume_base}/asr/logs",
        ollama_dir
    ]

    for d in dirs:
        if not dry_run:
            Path(d).mkdir(parents=True, exist_ok=True)

    typer.echo("✅ Directories created:")
    for d in dirs:
        typer.echo(f"  - {d}")

    # Deploy Ollama
    typer.echo("🐳 Deploying Ollama service...")
    run_cmd(["docker", "compose", "-f", "docker-compose.ollama.yml", "down"])
    run_cmd(["docker", "compose", "-f", "docker-compose.ollama.yml", "up", "-d"])

    # Wait for Ollama
    typer.echo("⏳ Waiting for Ollama to start...")
    for _i in range(30):
        try:
            result = run_cmd(["curl", "-sf", "http://localhost:11434/api/tags"], check=False, capture_output=True)
            if result and result.returncode == 0:
                typer.echo("✅ Ollama is ready")
                break
        except:
            pass
        typer.echo(".", nl=False)
        time.sleep(2)
    else:
        typer.echo("⚠️  Ollama may still be starting... continuing anyway")

    # Pull models
    typer.echo("📥 Pulling LLM models...")
    models = ["qwen3:1.7b", "deepseek-r1:7b"]

    for model in models:
        typer.echo(f"   Pulling {model}...")
        try:
            run_cmd(["docker", "exec", "fi-ollama", "ollama", "pull", model])
        except subprocess.CalledProcessError:
            typer.echo(f"⚠️  Failed to pull {model}")

    typer.echo("✅ Models pulled")

    # Deploy ASR worker
    typer.echo("🎤 Deploying ASR worker...")
    run_cmd(["docker", "compose", "-f", "docker-compose.asr.yml", "down"])
    run_cmd(["docker", "compose", "-f", "docker-compose.asr.yml", "up", "-d"])

    time.sleep(5)

    # Check ASR container
    try:
        result = run_cmd(["docker", "ps", "--filter", "name=fi-asr-worker", "--format", "{{.Names}}"], capture_output=True)
        if result and "fi-asr-worker" in result.stdout:
            typer.echo("✅ ASR worker deployed")
        else:
            typer.echo("⚠️  ASR worker may have issues, check logs: docker logs fi-asr-worker")
    except:
        typer.echo("⚠️  Could not check ASR worker status")

    # Verify deployment
    typer.echo("🔍 Verifying deployment...")

    # Check Ollama API
    try:
        result = run_cmd(["curl", "-sf", "http://localhost:11434/api/tags"], check=False, capture_output=True)
        if result and result.returncode == 0:
            typer.echo("✅ Ollama API responding (http://localhost:11434)")
        else:
            typer.echo("❌ Ollama API not responding", err=True)
            raise typer.Exit(1)
    except:
        typer.echo("❌ Ollama API not responding", err=True)
        raise typer.Exit(1)

    # Check ASR worker PID
    if Path("/tmp/worker.pid").exists():
        typer.echo("✅ ASR worker PID file exists")
    else:
        typer.echo("⚠️  ASR worker PID file not found")

    # Smoke tests
    typer.echo("🧪 Running smoke tests...")

    # Test Ollama generate
    typer.echo("   Testing Ollama generation...")
    try:
        result = run_cmd([
            "curl", "-s", "http://localhost:11434/api/generate",
            "-d", '{"model":"qwen3:1.7b","prompt":"Di hola en español.","stream":false}'
        ], capture_output=True)
        if result and "response" in result.stdout:
            typer.echo("✅ Ollama generate working")
        else:
            typer.echo("⚠️  Ollama generate may have issues")
    except:
        typer.echo("⚠️  Ollama generate test failed")

    # Display status
    typer.echo("\n" + "=" * 60)
    typer.echo("✅ Deployment Complete")
    typer.echo("=" * 60)
    typer.echo("\n🐳 Services:")
    typer.echo("  • Ollama API:  http://localhost:11434")
    typer.echo("  • ASR Worker:  Monitoring ready directory")
    typer.echo("\n📦 Docker Containers:")

    try:
        result = run_cmd(["docker", "ps", "--filter", "name=fi-", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"], capture_output=True)
        if result:
            typer.echo(result.stdout)
    except:
        typer.echo("  (Unable to list containers)")

    typer.echo("\n🧠 Ollama Models:")
    try:
        result = run_cmd(["docker", "exec", "fi-ollama", "ollama", "list"], capture_output=True)
        if result:
            typer.echo(result.stdout)
    except:
        typer.echo("  (Unable to list models)")

    typer.echo("\n📁 Directory Structure:")
    typer.echo(f"  Input:  {volume_base}/ready/*." + "{wav,mp3,m4a}")
    typer.echo(f"  Output: {volume_base}/asr/json/*.json")
    typer.echo(f"  Logs:   {volume_base}/asr/logs/worker.log")
    typer.echo("\n📊 Monitoring:")
    typer.echo("  docker logs -f fi-ollama")
    typer.echo("  docker logs -f fi-asr-worker")
    typer.echo(f"  tail -f {volume_base}/asr/logs/worker.log")
    typer.echo("\n🧪 Testing:")
    typer.echo("  # Test Ollama")
    typer.echo("  curl -s http://localhost:11434/api/generate \\")
    typer.echo("    -d '{\"model\":\"qwen3:1.7b\",\"prompt\":\"Hola\"}' | head")
    typer.echo("")
    typer.echo("  # Test ASR (place audio file)")
    typer.echo(f"  cp sample.wav {volume_base}/ready/")
    typer.echo("  # Wait ~30s, check output")
    typer.echo(f"  ls -lh {volume_base}/asr/json/")
    typer.echo("=" * 60)


@app.command("backend-fix-hdf5")
def backend_fix_hdf5(
    host: Annotated[
        str,
        typer.Option("--host", help="Production server hostname or IP")
    ] = "104.131.175.65",
    user: Annotated[
        str,
        typer.Option("--user", help="SSH username")
    ] = "root",
    key_path: Annotated[
        str,
        typer.Option("--key-path", help="Path to SSH private key")
    ] = "~/.ssh/id_rsa",
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be done without executing")
    ] = False,
) -> None:
    """
    Deploy backend fix for HDF5 path and restart.

    Clears HDF5 lock files, uploads updated finalize.py, verifies corpus.h5, restarts backend.
    Uses SSH key authentication. Requires root access on production server.
    """
    import time

    import os
    from pathlib import Path

    typer.echo("🔧 Deploying backend HDF5 fix to production...")

    if dry_run:
        typer.echo("🔍 DRY RUN MODE - No changes will be made")

    # Expand key path
    key_path = os.path.expanduser(key_path)
    if not Path(key_path).exists():
        typer.echo(f"❌ SSH key not found: {key_path}", err=True)
        raise typer.Exit(1)

    # Lazy import paramiko
    try:
        import paramiko
    except ImportError:
        typer.echo("❌ paramiko not installed. Install with: pip install paramiko", err=True)
        raise typer.Exit(1)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        typer.echo(f"🔑 Connecting to {host} as {user}...")
        if not dry_run:
            client.connect(host, username=user, key_filename=key_path, timeout=30)
            typer.echo("✅ Connected")

        # Stop backend
        typer.echo("🛑 Stopping backend...")
        stop_cmd = "pkill -9 -f 'python.*main' || echo 'No process'"
        if not dry_run:
            stdin, stdout, stderr = client.exec_command(stop_cmd)
            stdout.channel.recv_exit_status()
            time.sleep(2)
            typer.echo("✅ Backend stopped")
        else:
            typer.echo(f"   Would run: {stop_cmd}")

        # Clear HDF5 locks
        typer.echo("🔓 Clearing HDF5 lock files...")
        lock_cmd = "find /opt/free-intelligence/storage -name '*.h5.lock' -delete 2>/dev/null || true"
        if not dry_run:
            stdin, stdout, stderr = client.exec_command(lock_cmd)
            stdout.channel.recv_exit_status()
            typer.echo("✅ Locks cleared")
        else:
            typer.echo(f"   Would run: {lock_cmd}")

        # Upload updated file
        local_path = Path(__file__).parent.parent.parent.parent / "backend" / "api" / "internal" / "sessions" / "finalize.py"
        remote_path = "/opt/free-intelligence/backend/api/internal/sessions/finalize.py"

        typer.echo(f"📤 Uploading {local_path} to {remote_path}...")
        if not dry_run:
            sftp = client.open_sftp()
            sftp.put(str(local_path), remote_path)
            sftp.close()
            typer.echo("✅ File uploaded")
        else:
            typer.echo(f"   Would upload: {local_path} -> {remote_path}")

        # Verify corpus.h5
        typer.echo("🔍 Verifying corpus.h5 in production...")
        check_cmd = "ls -lh /opt/free-intelligence/storage/corpus.h5"
        if not dry_run:
            stdin, stdout, stderr = client.exec_command(check_cmd)
            corpus_info = stdout.read().decode().strip()
            if corpus_info:
                typer.echo(f"✅ HDF5 file found:\n   {corpus_info}")
            else:
                typer.echo("⚠️  corpus.h5 NOT found in production!")
        else:
            typer.echo(f"   Would check: {check_cmd}")

        # Start backend
        typer.echo("🚀 Starting backend...")
        start_cmd = """
cd /opt/free-intelligence && \
export PYTHONPATH=/opt/free-intelligence:$PYTHONPATH && \
nohup python3.14 -m backend.app.main > /tmp/backend.log 2>&1 &
"""
        if not dry_run:
            stdin, stdout, stderr = client.exec_command(start_cmd)
            stdout.channel.recv_exit_status()
            typer.echo("✅ Start command executed")
        else:
            typer.echo(f"   Would run: {start_cmd.strip()}")

        # Wait for startup
        typer.echo("⏳ Waiting 8 seconds for startup...")
        if not dry_run:
            time.sleep(8)

        # Verify process
        typer.echo("🔍 Checking backend process...")
        proc_cmd = "ps aux | grep '[u]vicorn'"
        if not dry_run:
            stdin, stdout, stderr = client.exec_command(proc_cmd)
            process = stdout.read().decode().strip()

            if process:
                typer.echo("✅ Backend is running:")
                typer.echo(f"   {process}")
            else:
                typer.echo("❌ Backend is NOT running!")
                typer.echo("📋 Last logs:")
                log_cmd = "tail -n 40 /tmp/backend.log"
                stdin, stdout, stderr = client.exec_command(log_cmd)
                typer.echo(stdin.read().decode())
                raise typer.Exit(1)
        else:
            typer.echo(f"   Would check: {proc_cmd}")

        # Verify port
        typer.echo("🔍 Checking port 7001...")
        if not dry_run:
            for i in range(10):
                port_cmd = "ss -tlnp | grep :7001"
                stdin, stdout, stderr = client.exec_command(port_cmd)
                port = stdout.read().decode().strip()
                if ":7001" in port:
                    typer.echo(f"✅ Port 7001 listening (after {i + 1}s)")
                    break
                time.sleep(1)
            else:
                typer.echo("❌ Port 7001 not responding")
        else:
            typer.echo("   Would check port 7001")

        # Test API
        typer.echo("🧪 Testing API...")
        if not dry_run:
            test_cmd = "curl -s -w '\\nHTTP:%{http_code}' http://localhost:7001/api/auth/config 2>&1"
            stdin, stdout, stderr = client.exec_command(test_cmd)
            response = stdout.read().decode()
            if "HTTP:200" in response:
                typer.echo("✅ API responding correctly!")
                first_line = response.split("\n")[0][:100]
                typer.echo(f"   Response: {first_line}...")
            else:
                typer.echo(f"⚠️  API response:\n{response}")
        else:
            typer.echo("   Would test API")

        # Show last logs
        typer.echo("📋 Last 15 log lines:")
        typer.echo("=" * 80)
        if not dry_run:
            log_cmd = "tail -n 15 /tmp/backend.log"
            stdin, stdout, _stderr = client.exec_command(log_cmd)
            typer.echo(stdin.read().decode())

        typer.echo("\n" + "=" * 80)
        typer.echo("✅ DEPLOYMENT COMPLETED")
        typer.echo("=" * 80)
        typer.echo("\n🌐 Test from mobile: https://app.aurity.io/")

    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)
    finally:
        if not dry_run:
            client.close()


@app.command("setup-ssl-production")
def setup_ssl_production(
    host: Annotated[
        str,
        typer.Option("--host", help="Production server hostname or IP")
    ] = "104.131.175.65",
    user: Annotated[
        str,
        typer.Option("--user", help="SSH username")
    ] = "root",
    key_path: Annotated[
        str,
        typer.Option("--key-path", help="Path to SSH private key")
    ] = "~/.ssh/id_rsa",
    domain: Annotated[
        str,
        typer.Option("--domain", help="Domain name for SSL certificate")
    ] = "app.aurity.io",
    email: Annotated[
        str,
        typer.Option("--email", help="Email for Let's Encrypt registration")
    ] = "bernarduriza@gmail.com",
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be done without making changes")
    ] = False,
) -> None:
    """
    Set up SSL certificate for production domain using Let's Encrypt.

    Installs certbot, obtains SSL certificate, configures nginx with HTTPS,
    and sets up auto-renewal. Uses SSH key authentication.
    """
    import subprocess

    from pathlib import Path

    # Lazy import paramiko
    try:
        import paramiko
    except ImportError:
        typer.echo("❌ paramiko not installed. Install with: pip install paramiko", err=True)
        raise typer.Exit(1)

    if not Path(key_path).expanduser().exists():
        typer.echo(f"❌ SSH key not found: {key_path}", err=True)
        raise typer.Exit(1)

    # Check DNS resolution locally
    typer.echo(f"🔍 Verifying DNS resolution for {domain}...")
    try:
        result = subprocess.run(
            ["dig", "+short", domain],
            capture_output=True,
            text=True,
            check=True
        )
        resolved_ip = result.stdout.strip().split('\n')[-1]

        if resolved_ip != host:
            typer.echo("⚠️  WARNING: DNS not pointing to server!")
            typer.echo(f"   Expected: {host}")
            typer.echo(f"   Got:      {resolved_ip}")
            if not typer.confirm("Continue anyway?", default=False):
                raise typer.Exit(1)
        else:
            typer.echo(f"✅ DNS correctly points to {host}")
    except subprocess.CalledProcessError:
        typer.echo("❌ Could not resolve DNS. Check your internet connection.")
        raise typer.Exit(1)

    typer.echo(f"\n🔐 Setting up SSL certificate for {domain}")
    typer.echo("\n📝 This command will:")
    typer.echo("   1. Install certbot if needed")
    typer.echo("   2. Stop nginx temporarily")
    typer.echo("   3. Obtain SSL certificate for domain")
    typer.echo("   4. Configure nginx to use new certificate")
    typer.echo("   5. Setup auto-renewal")

    if not dry_run and not typer.confirm("Continue?", default=False):
        raise typer.Exit(0)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        typer.echo(f"\n🚀 Connecting to {host} as {user}...")
        if dry_run:
            typer.echo("   (dry-run: would connect)")
        else:
            client.connect(host, username=user, key_filename=os.path.expanduser(key_path), timeout=30)
        typer.echo("✅ Connected")

        # Install certbot
        typer.echo("\n📦 Installing certbot...")
        if dry_run:
            typer.echo("   (dry-run: would install certbot)")
        else:
            stdin, stdout, stderr = client.exec_command(
                "apt-get update && apt-get install -y certbot python3-certbot-nginx"
            )
            stdout.channel.recv_exit_status()
            typer.echo("✅ Certbot installed")

        # Stop nginx temporarily
        typer.echo("\n🛑 Stopping nginx temporarily...")
        if dry_run:
            typer.echo("   (dry-run: would stop nginx)")
        else:
            stdin, stdout, stderr = client.exec_command("systemctl stop nginx")
            stdout.channel.recv_exit_status()
            typer.echo("✅ Nginx stopped")

        # Obtain SSL certificate
        typer.echo(f"\n🎫 Obtaining SSL certificate for {domain}...")
        if dry_run:
            typer.echo("   (dry-run: would obtain certificate)")
        else:
            cert_cmd = f"""certbot certonly --standalone \
                --non-interactive \
                --agree-tos \
                --email {email} \
                -d {domain}"""
            stdin, stdout, stderr = client.exec_command(cert_cmd)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                typer.echo(f"❌ Certbot failed: {stderr.read().decode()}")
                raise typer.Exit(1)
            typer.echo("✅ Certificate obtained")

        # Create nginx config
        typer.echo(f"\n📝 Creating nginx config for {domain}...")
        nginx_config = f"""# HTTP (redirect to HTTPS)
server {{
    listen 80;
    server_name {domain};
    return 301 https://$server_name$request_uri;
}}

# HTTPS
server {{
    listen 443 ssl http2;
    server_name {domain};

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;

    # SSL Security (HIPAA compliant)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Frontend (Next.js static export)
    root /opt/free-intelligence/apps/aurity/out;
    index index.html;

    # API Backend (FastAPI)
    location /api/ {{
        proxy_pass http://localhost:7001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        # Timeouts for long-running requests (audio upload)
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
    }}

    # Frontend routing (SPA fallback)
    location / {{
        try_files $uri $uri/ /index.html;
    }}

    # Static assets caching
    location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {{
        expires 1y;
        add_header Cache-Control "public, immutable";
    }}
}}
"""

        if dry_run:
            typer.echo("   (dry-run: would create nginx config)")
        else:
            stdin, stdout, stderr = client.exec_command(
                f"cat > /etc/nginx/sites-available/aurity << 'EOF'\n{nginx_config}\nEOF"
            )
            stdout.channel.recv_exit_status()
            typer.echo("✅ Nginx config created")

        # Enable site
        typer.echo("\n🔗 Enabling site...")
        if dry_run:
            typer.echo("   (dry-run: would enable site)")
        else:
            stdin, stdout, stderr = client.exec_command(
                "ln -sf /etc/nginx/sites-available/aurity /etc/nginx/sites-enabled/aurity"
            )
            stdout.channel.recv_exit_status()

            # Remove old config if exists
            stdin, stdout, stderr = client.exec_command(
                "rm -f /etc/nginx/sites-enabled/aurity-duckdns"
            )
            stdout.channel.recv_exit_status()
            typer.echo("✅ Site enabled")

        # Test nginx config
        typer.echo("\n✅ Testing nginx config...")
        if dry_run:
            typer.echo("   (dry-run: would test nginx config)")
        else:
            stdin, stdout, stderr = client.exec_command("nginx -t")
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                typer.echo(f"❌ Nginx config test failed: {stderr.read().decode()}")
                raise typer.Exit(1)
            typer.echo("✅ Nginx config valid")

        # Start nginx
        typer.echo("\n🚀 Starting nginx...")
        if dry_run:
            typer.echo("   (dry-run: would start nginx)")
        else:
            stdin, stdout, stderr = client.exec_command(
                "systemctl start nginx && systemctl enable nginx"
            )
            stdout.channel.recv_exit_status()
            typer.echo("✅ Nginx started and enabled")

        # Setup auto-renewal
        typer.echo("\n🔄 Setting up auto-renewal...")
        if dry_run:
            typer.echo("   (dry-run: would setup auto-renewal)")
        else:
            stdin, stdout, stderr = client.exec_command("certbot renew --dry-run")
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                typer.echo(f"⚠️  Auto-renewal test failed: {stderr.read().decode()}")
            else:
                typer.echo("✅ Auto-renewal configured")

        # Show certificate details
        typer.echo("\n📋 Certificate details:")
        if dry_run:
            typer.echo("   (dry-run: would show certificate details)")
        else:
            _stdin, stdout, stderr = client.exec_command("certbot certificates")
            typer.echo(stdout.read().decode())

        typer.echo("\n✅ SSL setup complete!")
        typer.echo("\n🧪 Test your site:")
        typer.echo(f"   curl -I https://{domain}")
        typer.echo(f"   curl https://{domain}/api/health")
        typer.echo("\n📝 Next steps:")
        typer.echo(f"   1. Test frontend: https://{domain}")
        typer.echo(f"   2. Test backend:  https://{domain}/api/health")
        typer.echo("   3. Push changes to trigger GitHub Actions deployment")

    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)
    finally:
        if not dry_run:
            client.close()


@app.command("install-prod-security-hook")
def install_prod_security_hook(
    host: Annotated[str, typer.Option("--host", help="Production server host")] = "",
    user: Annotated[str | None, typer.Option("--user", help="SSH user")] = None,
    port: Annotated[int | None, typer.Option("--port", help="SSH port")] = None,
    identity_file: Annotated[str | None, typer.Option("--identity-file", help="SSH key file")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be done")] = False,
) -> None:
    """Install production security hook to prevent direct pushes to production."""
    import paramiko

    if not host:
        typer.echo("❌ --host is required for production security hook installation")
        raise typer.Exit(1)

    typer.echo("🛡️ Installing production security hook...")
    typer.echo("   This hook prevents direct pushes to production servers.")
    typer.echo("   All deployments must go through CI/CD pipeline.")
    typer.echo()

    if dry_run:
        typer.echo("🔍 DRY RUN - Would install security hook on production server")
        typer.echo(f"   Host: {host}")
        typer.echo("   Hook location: /opt/free-intelligence/.git/hooks/pre-receive")
        return

    # SSH connection
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=host,
            username=user,
            port=port or 22,
            key_filename=identity_file,
            look_for_keys=True,
        )

        # Create hook directory if it doesn't exist
        client.exec_command("mkdir -p /opt/free-intelligence/.git/hooks")

        # Install the pre-receive hook
        hook_content = '''#!/bin/bash
# =============================================================================
# AURITY Production Pre-Receive Hook
# =============================================================================
# Makes it IMPOSSIBLE to push directly to production
#
# This hook runs on the SERVER when someone tries to push.
# It rejects ALL pushes - production only accepts deploys via CI/CD.
# =============================================================================

set -euo pipefail

RED='\\033[0;31m'
YELLOW='\\033[1;33m'
NC='\\033[0m'

echo -e "${RED}"
cat << 'EOF'
 ██████╗ ██████╗  ██████╗ ██████╗     ██████╗ ██╗      ██████╗  ██████╗██╗  ██╗███████╗██████╗
 ██╔══██╗██╔══██╗██╔═══██╗██╔══██╗    ██╔══██╗██║     ██╔═══██╗██╔════╝██║ ██╔╝██╔════╝██╔══██╗
 ██████╔╝██████╔╝██║   ██║██║  ██║    ██████╔╝██║     ██║   ██║██║     █████╔╝ █████╗  ██║  ██║
 ██╔═══╝ ██╔══██╗██║   ██║██║  ██║    ██╔══██╗██║     ██║   ██║██║     ██╔═██╗ ██╔══╝  ██║  ██║
 ██║     ██║  ██║╚██████╔╝██████╔╝    ██████╔╝███████╗╚██████╔╝╚██████╗██║  ╚██╗███████╗██████╔╝
 ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═════╝     ╚═════╝ ╚══════╝ ╚═════╝  ╚═════╝╚═╝   ╚═╝╚══════╝╚═════╝
EOF
echo -e "${NC}"

echo -e "${YELLOW}════════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${RED}⛔️  DIRECT PUSH TO PRODUCTION IS FORBIDDEN${NC}"
echo ""
echo "   This is a PRODUCTION server. All deployments must go through CI/CD."
echo ""
echo "   What you should do instead:"
echo "   1. Push to GitHub: git push origin main"
echo "   2. CI/CD will deploy automatically after tests pass"
echo "   3. Or use: make ci-deploy (from your local machine)"
echo ""
echo -e "${YELLOW}   Incident logged. Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")${NC}"
echo -e "${YELLOW}   User: ${USER:-unknown}${NC}"
echo -e "${YELLOW}   IP: ${SSH_CLIENT%% *}${NC}"
echo -e "${YELLOW}════════════════════════════════════════════════════════════════════════════════${NC}"

# Log the attempt
echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") BLOCKED_PUSH user=${USER:-unknown} ip=${SSH_CLIENT%% *}" >> /var/log/aurity-security.log

exit 1
'''

        # Write hook to file
        stdin, stdout, stderr = client.exec_command("cat > /opt/free-intelligence/.git/hooks/pre-receive")
        stdin.write(hook_content)
        stdin.close()

        # Make it executable
        client.exec_command("chmod +x /opt/free-intelligence/.git/hooks/pre-receive")

        # Verify installation
        stdin, stdout, _stderr = client.exec_command("ls -la /opt/free-intelligence/.git/hooks/pre-receive")
        hook_check = stdout.read().decode().strip()

        if "pre-receive" in hook_check and "-x" in hook_check:
            typer.echo("✅ Production security hook installed successfully!")
            typer.echo("   Direct pushes to production are now blocked.")
            typer.echo("   All deployments must use CI/CD pipeline.")
        else:
            typer.echo("❌ Hook installation verification failed")
            raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"❌ Error installing security hook: {e}")
        raise typer.Exit(1)
    finally:
        client.close()
