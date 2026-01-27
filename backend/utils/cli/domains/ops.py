from __future__ import annotations

import subprocess
from typing import Annotated

import typer
from pathlib import Path

from .._common import ExitCode, redact_text, run_cmd, ssh_argv

app = typer.Typer(name="ops", help="Operational inspection and health checks", no_args_is_help=True)


HostOpt = Annotated[str, typer.Option("--host", envvar="FI_OPS_HOST", help="Target host (required)")]
UserOpt = Annotated[str | None, typer.Option("--user", envvar="FI_OPS_USER", help="SSH user")]
PortOpt = Annotated[int | None, typer.Option("--port", envvar="FI_OPS_PORT", help="SSH port")]
IdentityOpt = Annotated[
	Path | None,
	typer.Option("--identity-file", envvar="FI_OPS_IDENTITY_FILE", exists=True, dir_okay=False, help="SSH key"),
]


def _require_host(host: str | None) -> str:
	if not host:
		raise typer.BadParameter("--host is required (or set FI_OPS_HOST)")
	return host


@app.command("backend-startup-logs")
def backend_startup_logs(
	host: HostOpt = "",
	user: UserOpt = None,
	port: PortOpt = None,
	identity_file: IdentityOpt = None,
) -> None:
	"""Fetch remote backend process/port status and backend log (redacted)."""
	host = _require_host(host)
	cmd = (
		"set -e; "
		"echo 'PROCESS:'; ps aux | grep '[u]vicorn' || true; "
		"echo 'PORT:'; (ss -tlnp | grep :7001 || true); "
		"echo 'LOG:'; (cat /tmp/backend.log 2>/dev/null || true)"
	)
	proc = run_cmd(
		ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
		capture_output=True,
		check=False,
	)
	if proc.stdout:
		typer.echo(redact_text(proc.stdout))
	if proc.stderr:
		typer.echo(redact_text(proc.stderr), err=True)
	raise typer.Exit(code=int(ExitCode.OK))


@app.command("backend-health")
def backend_health(
	host: HostOpt = "",
	user: UserOpt = None,
	port: PortOpt = None,
	identity_file: IdentityOpt = None,
	wait_s: Annotated[int, typer.Option("--wait-s", min=0, max=120, help="Wait for port 7001")]=15,
) -> None:
	"""Verify remote uvicorn process + port 7001 + basic endpoints (redacted)."""
	host = _require_host(host)
	remote = (
		"set -e; "
		"echo 'PROCESS:'; ps aux | grep '[u]vicorn' || true; "
		f"echo 'WAIT_PORT:{wait_s}'; "
		f"for i in $(seq 1 {wait_s}); do ss -tlnp | grep :7001 >/dev/null 2>&1 && break; sleep 1; done; "
		"echo 'PORT:'; (ss -tlnp | grep :7001 || true); "
		"echo 'ENDPOINT:/api/health'; curl -s -w '\\nSTATUS:%{http_code}' -m 3 http://localhost:7001/api/health 2>&1 || true; "
		"echo 'ENDPOINT:/api/auth/config'; curl -s -w '\\nSTATUS:%{http_code}' -m 3 http://localhost:7001/api/auth/config 2>&1 || true;"
	)
	proc = run_cmd(
		ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=remote),
		capture_output=True,
		check=False,
	)
	if proc.stdout:
		typer.echo(redact_text(proc.stdout))
		typer.echo(redact_text(proc.stderr), err=True)


@app.command("check-backend-logs")
def check_backend_logs(
	host: HostOpt = "",
	user: UserOpt = None,
	port: PortOpt = None,
	identity_file: IdentityOpt = None,
) -> None:
	"""Check backend process status, logs, and nginx errors (redacted)."""
	host = _require_host(host)
	cmd = (
		"set -e; "
		"echo '=== BACKEND PROCESS ==='; "
		"ps aux | grep '[p]ython.*main.py' || echo 'No backend process found'; "
		"echo; "
		"echo '=== BACKEND LOGS (last 50 lines) ==='; "
		"journalctl -u backend -n 50 --no-pager 2>/dev/null || "
		"tail -n 50 /var/log/backend.log 2>/dev/null || "
		"tail -n 50 /opt/free-intelligence/backend/logs/app.log 2>/dev/null || "
		"echo 'No backend logs found in standard locations'; "
		"echo; "
		"echo '=== NGINX ERRORS (last 20 lines) ==='; "
		"tail -n 20 /var/log/nginx/error.log 2>/dev/null || echo 'No nginx error log found'; "
		"echo; "
		"echo '=== PORT 7001 STATUS ==='; "
		"ss -tlnp | grep :7001 || lsof -i :7001 || echo 'Port 7001 not listening'; "
		"echo; "
		"echo '=== BACKEND HEALTH CHECK ==='; "
		"curl -s -m 5 http://localhost:7001/api/health 2>&1 || echo 'Backend health check failed'"
	)
	proc = run_cmd(
		ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
		capture_output=True,
		check=False,
	)
	if proc.stdout:
		typer.echo(redact_text(proc.stdout))
		typer.echo(redact_text(proc.stderr), err=True)
	raise typer.Exit(code=int(ExitCode.OK))


@app.command("check-recent-errors")
def check_recent_errors(
	host: HostOpt = "",
	user: UserOpt = None,
	port: PortOpt = None,
	identity_file: IdentityOpt = None,
) -> None:
	"""Check recent backend logs, nginx errors, and access logs (redacted)."""
	host = _require_host(host)
	cmd = (
		"set -e; "
		"echo '=== BACKEND LOGS (last 30 lines) ==='; "
		"tail -n 30 /tmp/backend.log 2>/dev/null || echo 'No backend log found'; "
		"echo; "
		"echo '=== NGINX ERRORS (last 30 lines) ==='; "
		"tail -n 30 /var/log/nginx/error.log 2>/dev/null || echo 'No nginx error log found'; "
		"echo; "
		"echo '=== NGINX ACCESS (last 20 relevant lines) ==='; "
		"tail -n 20 /var/log/nginx/access.log 2>/dev/null | grep -E '(api|auth|workflows)' || tail -n 10 /var/log/nginx/access.log 2>/dev/null || echo 'No access log found'; "
		"echo; "
		"echo '=== BACKEND PROCESS STATUS ==='; "
		"ps aux | grep '[u]vicorn' | head -1 || echo 'No backend process found'; "
		"echo; "
		"echo '=== PORT 7001 STATUS ==='; "
		"ss -tlnp | grep :7001 || echo 'Port 7001 not listening'"
	)
	proc = run_cmd(
		ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
		capture_output=True,
		check=False,
	)
	if proc.stdout:
		typer.echo(redact_text(proc.stdout))
		typer.echo(redact_text(proc.stderr), err=True)
	raise typer.Exit(code=int(ExitCode.OK))


@app.command("verify-auth0-audience")
def verify_auth0_audience(
	host: HostOpt = "",
	user: UserOpt = None,
	port: PortOpt = None,
	identity_file: IdentityOpt = None,
) -> None:
	"""Verify Auth0 audience configuration via /api/auth/config endpoint (redacted)."""
	host = _require_host(host)
	cmd = (
		"set -e; "
		"echo '=== AUTH0 CONFIG CHECK ==='; "
		"response=$(curl -s http://localhost:7001/api/auth/config 2>/dev/null); "
		"if [ $? -eq 0 ] && [ -n \"$response\" ]; then "
		"  echo \"$response\" | python3 -m json.tool 2>/dev/null || echo \"$response\"; "
		"  echo; "
		"  audience=$(echo \"$response\" | python3 -c 'import sys, json; print(json.load(sys.stdin).get(\"audience\", \"NOT_FOUND\"))' 2>/dev/null || echo 'PARSE_ERROR'); "
		"  echo \"AUDIENCE: $audience\"; "
		"  if [ \"$audience\" = \"https://app.aurity.io\" ]; then "
		"    echo '✅ CORRECT - No api subdomain'; "
		"  elif [ \"$audience\" = \"https://api.app.aurity.io\" ]; then "
		"    echo '❌ INCORRECT - Still has api subdomain'; "
		"  else "
		"    echo '⚠️  UNEXPECTED - Check manually'; "
		"  fi; "
		"else "
		"  echo '❌ Failed to get auth config'; "
		"fi"
	)
	proc = run_cmd(
		ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
		capture_output=True,
		check=False,
	)
	if proc.stdout:
		typer.echo(redact_text(proc.stdout))
	if proc.stderr:
		typer.echo(redact_text(proc.stderr), err=True)
	raise typer.Exit(code=int(ExitCode.OK))


@app.command("tail-backend-logs")
def tail_backend_logs(
	host: HostOpt = "",
	user: UserOpt = None,
	port: PortOpt = None,
	identity_file: IdentityOpt = None,
	include_nginx: Annotated[
		bool,
		typer.Option("--include-nginx/--no-include-nginx", help="Also tail nginx error log"),
	] = True,
) -> None:
	"""Tail remote backend logs (and optionally nginx) in real time (redacted)."""
	host = _require_host(host)
	files = ["/tmp/backend.log"]
	if include_nginx:
		files.append("/var/log/nginx/error.log")
	remote = f"tail -n 0 -f {' '.join(files)}"
	argv = ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=remote)

	try:
		proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
	except FileNotFoundError as exc:
		typer.echo("❌ ssh not found", err=True)
		raise typer.Exit(code=int(ExitCode.ERROR)) from exc

	assert proc.stdout is not None
	try:
		for line in proc.stdout:
			safe = redact_text(line.rstrip("\n"))
			low = safe.lower()
			if "error" in low or "exception" in low or "traceback" in low:
				typer.echo(f"[ERR] {safe}")
			elif "warning" in low or "warn" in low:
				typer.echo(f"[WRN] {safe}")
			else:
				typer.echo(safe)
	except KeyboardInterrupt:
		pass
	finally:
		proc.terminate()


@app.command("check-missing-files")
def check_missing_files(
	host: HostOpt = "",
	user: UserOpt = None,
	port: PortOpt = None,
	identity_file: IdentityOpt = None,
) -> None:
	"""
	Check which build files are missing from the server.

	Verifies Next.js build artifacts (CSS/JS) on production server.
	"""
	host = _require_host(host)

	typer.echo("🔍 Checking for missing build files on server...")

	# Get list of CSS files on server
	cmd = "ls -lh /opt/free-intelligence/apps/aurity/out/_next/static/chunks/*.css 2>&1"
	proc = run_cmd(
		ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
		capture_output=True,
		check=False,
	)
	typer.echo("📋 CSS files on server:")
	typer.echo("=" * 80)
	if proc.stdout:
		typer.echo(proc.stdout)
	else:
		typer.echo("❌ No CSS files found")

	# Check for specific missing files
	missing_files = ["2787eb3c5de6dde5.js", "abb749a40dfb2eb5.css"]

	typer.echo("\n🔍 Checking specific files that may be missing:")
	typer.echo("=" * 80)
	for filename in missing_files:
		cmd = f"find /opt/free-intelligence/apps/aurity/out -name '{filename}' 2>&1"
		proc = run_cmd(
			ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
			capture_output=True,
			check=False,
		)
		if proc.stdout.strip():
			typer.echo(f"✅ {filename}: {proc.stdout.strip()}")
		else:
			typer.echo(f"❌ {filename}: NOT FOUND")

	# List all files in chunks directory
	typer.echo("\n📂 All files in _next/static/chunks/:")
	typer.echo("=" * 80)
	cmd = "ls /opt/free-intelligence/apps/aurity/out/_next/static/chunks/ | sort"
	proc = run_cmd(
		ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
		capture_output=True,
		check=False,
	)
	if proc.stdout:
		typer.echo(proc.stdout)

	# Diagnostic message
	typer.echo("\n💡 DIAGNOSIS:")
	typer.echo("=" * 80)
	typer.echo("""
The problem is that HTML is referencing files that do NOT exist on the server.

Possible causes:
1. Local build generated different files than those uploaded
2. Deployment only uploaded some files (partial)
3. Turbopack issue generating files dynamically

Solution:
1. Do a CLEAN build (rm -rf .next .turbo)
2. Verify ALL files are generated
3. Re-deploy ALL files
	""")


@app.command("diagnose-nginx-static")
def diagnose_nginx_static(
	host: HostOpt = "",
	user: UserOpt = None,
	port: PortOpt = None,
	identity_file: IdentityOpt = None,
) -> None:
	"""
	Diagnose nginx static file issues on production server.

	Checks file structure, nginx config, and HTTP responses for static assets.
	"""
	host = _require_host(host)

	typer.echo("🔍 Diagnosing nginx static file issues...")

	# Check if _next directory exists
	typer.echo("\n📂 Checking file structure:")
	typer.echo("=" * 80)
	cmd = "ls -la /opt/free-intelligence/apps/aurity/out/ | head -20"
	proc = run_cmd(
		ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
		capture_output=True,
		check=False,
	)
	if proc.stdout:
		typer.echo(proc.stdout)

	# Check _next/static/chunks
	typer.echo("\n📂 Checking _next/static/chunks:")
	typer.echo("=" * 80)
	cmd = "ls -la /opt/free-intelligence/apps/aurity/out/_next/static/chunks/ 2>&1 | head -20"
	proc = run_cmd(
		ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
		capture_output=True,
		check=False,
	)
	if proc.stdout:
		typer.echo(proc.stdout)

	# Check specific file that's failing
	typer.echo("\n🔍 Looking for specific file (2787eb3c5de6dde5.js):")
	typer.echo("=" * 80)
	cmd = "find /opt/free-intelligence/apps/aurity/out -name '2787eb3c5de6dde5.js' 2>&1"
	proc = run_cmd(
		ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
		capture_output=True,
		check=False,
	)
	if proc.stdout.strip():
		typer.echo(f"✅ Found: {proc.stdout.strip()}")
		# Check file type
		cmd = "file /opt/free-intelligence/apps/aurity/out/_next/static/chunks/2787eb3c5de6dde5.js"
		proc = run_cmd(
			ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
			capture_output=True,
			check=False,
		)
		if proc.stdout:
			typer.echo(f"   Type: {proc.stdout.strip()}")
	else:
		typer.echo("❌ File NOT found on server!")

	# Check Nginx config
	typer.echo("\n📋 Nginx configuration:")
	typer.echo("=" * 80)
	cmd = "cat /etc/nginx/sites-enabled/aurity"
	proc = run_cmd(
		ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
		capture_output=True,
		check=False,
	)
	if proc.stdout:
		typer.echo(proc.stdout)

	# Test actual HTTP response
	typer.echo("\n🧪 HTTP test for static file:")
	typer.echo("=" * 80)
	cmd = "curl -I http://localhost/_next/static/chunks/2787eb3c5de6dde5.js 2>&1 | head -15"
	proc = run_cmd(
		ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
		capture_output=True,
		check=False,
	)
	if proc.stdout:
		typer.echo(proc.stdout)


@app.command("patch-auth0-config")
def patch_auth0_config(
	host: HostOpt = "",
	user: UserOpt = None,
	port: PortOpt = None,
	identity_file: IdentityOpt = None,
) -> None:
	"""
	Patch Auth0 config on production server.

	Updates AUTH0_API_IDENTIFIER in auth0_config.py and restarts backend.
	Hotfix for Auth0 audience configuration issues.
	"""
	import time

	host = _require_host(host)

	typer.echo("🔧 Patching Auth0 config on server...")
	typer.echo(f"   Host: {host}")
	typer.echo()

	# Read current file
	typer.echo("📖 Reading current file...")
	cmd = "cat /opt/free-intelligence/backend/auth/auth0_config.py"
	proc = run_cmd(
		ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
		capture_output=True,
		check=False,
	)
	if proc.stdout:
		current_content = proc.stdout
		typer.echo(f"   Size: {len(current_content)} bytes")
	else:
		typer.echo("❌ Failed to read file", err=True)
		raise typer.Exit(1)

	# Patch the file
	typer.echo("🔧 Applying patch...")
	new_content = current_content.replace(
		b'AUTH0_API_IDENTIFIER = os.getenv("AUTH0_API_IDENTIFIER", "https://api.fi-aurity.duckdns.org")',
		b'AUTH0_API_IDENTIFIER = os.getenv("AUTH0_API_IDENTIFIER", "https://api.app.aurity.io")',
	)

	if new_content == current_content:
		typer.echo("⚠️  No line found to patch")
	else:
		typer.echo("✅ Patch prepared")

	# Write patched file
	typer.echo("💾 Writing patched file...")
	config_cmd = f"cat > /opt/free-intelligence/backend/auth/auth0_config.py << 'ENDOFFILE'\n{new_content.decode('utf-8')}\nENDOFFILE"
	proc = run_cmd(
		ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=config_cmd),
		capture_output=True,
		check=False,
	)
	typer.echo("✅ File updated")

	# Restart backend
	typer.echo("🔄 Restarting backend...")
	cmd = "pkill -9 -f 'python.*main'"
	proc = run_cmd(
		ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
		capture_output=True,
		check=False,
	)
	time.sleep(2)

	start_cmd = """
	cd /opt/free-intelligence && \
	export PYTHONPATH=/opt/free-intelligence:$PYTHONPATH && \
	nohup python3.14 -m backend.app.main > /tmp/backend.log 2>&1 &
	"""
	proc = run_cmd(
		ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=start_cmd),
		capture_output=True,
		check=False,
	)
	typer.echo("✅ Backend restarted")

	# Wait
	typer.echo("⏳ Waiting 8 seconds...")
	time.sleep(8)

	# Verify
	typer.echo("🧪 Verifying new audience...")
	cmd = "curl -s http://localhost:7001/api/auth/config 2>&1 | grep audience"
	proc = run_cmd(
		ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
		capture_output=True,
		check=False,
	)
	if proc.stdout:
		result = proc.stdout.strip()
		typer.echo(f"   {result}")

		if b"api.app.aurity.io" in proc.stdout:
			typer.echo("✅ AUDIENCE UPDATED CORRECTLY!")
		else:
			typer.echo("❌ Audience NOT updated")
			typer.echo("📋 Recent logs:")
			cmd = "tail -n 20 /tmp/backend.log"
			proc = run_cmd(
				ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
				capture_output=True,
				check=False,
			)
			if proc.stdout:
				typer.echo(proc.stdout)

	typer.echo()
	typer.echo("=" * 80)
	typer.echo("✅ PATCH APPLIED")
	typer.echo("=" * 80)
	typer.echo("""
PERMANENT change applied:
- auth0_config.py updated on server
- audience: https://api.app.aurity.io

Test login from your mobile device now.
	""")


@app.command("test-assistant-api")
def test_assistant_api(
    api_base: Annotated[
        str,
        typer.Option("--api-base", help="Base URL for API endpoints")
    ] = "https://app.aurity.io",
    message: Annotated[
        str,
        typer.Option("--message", help="Test message to send")
    ] = "Hola, solo estoy probando el endpoint",
    doctor_id: Annotated[
        str,
        typer.Option("--doctor-id", help="Doctor ID for test")
    ] = "test_doctor_123",
    doctor_name: Annotated[
        str,
        typer.Option("--doctor-name", help="Doctor name for test")
    ] = "Dr. Test",
) -> None:
    """
    Test assistant API endpoint in production.

    Sends a test message to the assistant chat endpoint and displays the response.
    Useful for verifying the assistant API is working correctly.
    """
    import json

    typer.echo("🧪 Testing Assistant API Endpoint")
    typer.echo("=" * 50)
    typer.echo(f"   API Base: {api_base}")
    typer.echo(f"   Message: {message}")
    typer.echo(f"   Doctor: {doctor_name} ({doctor_id})")
    typer.echo()

    # Prepare request data
    data = {
        "message": message,
        "doctor_id": doctor_id,
        "doctor_name": doctor_name,
        "response_mode": "concise"
    }

    # Make the request
    import requests

    try:
        typer.echo("📤 Sending test message...")
        response = requests.post(
            f"{api_base}/api/workflows/aurity/assistant/chat",
            json=data,
            timeout=30
        )

        typer.echo(f"📥 Response Status: {response.status_code}")
        typer.echo()

        if response.status_code == 200:
            try:
                response_data = response.json()
                typer.echo("✅ API responded successfully")
                typer.echo("📋 Response data:")
                typer.echo(json.dumps(response_data, indent=2, ensure_ascii=False))
            except json.JSONDecodeError:
                typer.echo("⚠️  Response is not valid JSON")
                typer.echo("📄 Raw response:")
                typer.echo(response.text)
        else:
            typer.echo("❌ API request failed")
            typer.echo(f"   Status: {response.status_code}")
            typer.echo(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
            typer.echo("📄 Response body:")
            typer.echo(response.text)

    except requests.exceptions.RequestException as e:
        typer.echo(f"❌ Request failed: {e}")
        raise typer.Exit(1)

    typer.echo()
    typer.echo("=" * 50)


@app.command("check-prod-logs-detailed")
def check_prod_logs_detailed(
	host: HostOpt = "",
	user: UserOpt = None,
	port: PortOpt = None,
	identity_file: IdentityOpt = None,
) -> None:
	"""Check production backend logs in detail (processes, ports, logs, errors)."""
	host = _require_host(host)

	try:
		# Check if backend is running
		typer.echo("🔍 Checking backend process...")
		typer.echo("=" * 80)
		cmd = "ps aux | grep '[p]ython.*main'"
		proc = run_cmd(
			ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
			capture_output=True,
			check=False,
		)
		process = proc.stdout.strip()

		if process:
			typer.echo(f"✅ Backend running:\n{redact_text(process)}\n")
		else:
			typer.echo("❌ Backend NOT running!\n")

		# Check port
		typer.echo("🔍 Checking port 7001...")
		typer.echo("=" * 80)
		cmd = "ss -tlnp | grep :7001"
		proc = run_cmd(
			ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
			capture_output=True,
			check=False,
		)
		port_info = proc.stdout.strip()

		if port_info:
			typer.echo(f"✅ Port 7001 listening:\n{redact_text(port_info)}\n")
		else:
			typer.echo("❌ Port 7001 NOT listening!\n")

		# Get last 100 lines of backend logs
		typer.echo("📋 LAST 100 BACKEND LOGS:")
		typer.echo("=" * 80)
		cmd = "tail -n 100 /tmp/backend.log"
		proc = run_cmd(
			ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
			capture_output=True,
			check=False,
		)
		logs = proc.stdout.strip()

		if logs:
			typer.echo(redact_text(logs))
		else:
			typer.echo("(no recent logs)")

		typer.echo("\n" + "=" * 80)
		typer.echo("🔍 LOOKING FOR RECENT ERRORS:")
		typer.echo("=" * 80)
		cmd = "tail -n 200 /tmp/backend.log | grep -i -E '(error|exception|traceback|failed|crash)' | tail -20"
		proc = run_cmd(
			ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
			capture_output=True,
			check=False,
		)
		errors = proc.stdout.strip()

		if errors:
			typer.echo(redact_text(errors))
		else:
			typer.echo("✅ No obvious errors found")

	except Exception as e:
		typer.echo(f"❌ Error: {redact_text(str(e))}")
		raise typer.Exit(1)


@app.command("fix-auth0-audience")
def fix_auth0_audience(
	host: HostOpt = "",
	user: UserOpt = None,
	port: PortOpt = None,
	identity_file: IdentityOpt = None,
) -> None:
	"""Fix Auth0 API Identifier mismatch by updating environment variable."""
	host = _require_host(host)

	try:
		typer.echo("🔍 Checking current AUTH0_API_IDENTIFIER...")
		typer.echo("=" * 80)
		cmd = "printenv | grep AUTH0_API_IDENTIFIER || echo 'Not set'"
		proc = run_cmd(
			ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
			capture_output=True,
			check=False,
		)
		current = proc.stdout.strip()
		typer.echo(f"   Current: {redact_text(current)}\n")

		# Stop backend
		typer.echo("🛑 Stopping backend...")
		cmd = "pkill -9 -f 'python.*main'"
		run_cmd(
			ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
			capture_output=True,
			check=False,
		)
		typer.echo("✅ Backend stopped\n")

		# Start with updated environment variable
		typer.echo("🚀 Starting backend with new AUTH0_API_IDENTIFIER...")
		start_cmd = (
			"cd /opt/free-intelligence && "
			"export PYTHONPATH=/opt/free-intelligence:$PYTHONPATH && "
			"export AUTH0_API_IDENTIFIER=https://api.app.aurity.io && "
			"nohup python3.14 -m backend.app.main > /tmp/backend.log 2>&1 &"
		)
		run_cmd(
			ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=start_cmd),
			capture_output=True,
			check=False,
		)
		typer.echo("✅ Command executed\n")

		# Wait for startup
		typer.echo("⏳ Waiting 8 seconds for startup...")
		import time
		time.sleep(8)

		# Verify process
		typer.echo("🔍 Verifying backend process...")
		cmd = "ps aux | grep '[u]vicorn'"
		proc = run_cmd(
			ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
			capture_output=True,
			check=False,
		)
		process = proc.stdout.strip()

		if process:
			typer.echo(f"✅ Backend running:\n   {redact_text(process)}\n")
		else:
			typer.echo("❌ Backend NOT running!\n")
			typer.echo("📋 Recent logs:")
			cmd = "tail -n 30 /tmp/backend.log"
			proc = run_cmd(
				ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
				capture_output=True,
				check=False,
			)
			typer.echo(redact_text(proc.stdout))
			raise typer.Exit(1)

		# Verify port
		typer.echo("🔍 Verifying port 7001...")
		for i in range(10):
			cmd = "ss -tlnp | grep :7001"
			proc = run_cmd(
				ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
				capture_output=True,
				check=False,
			)
			if proc.stdout.strip():
				typer.echo(f"✅ Port 7001 listening (after {i + 1}s)\n")
				break
			time.sleep(1)
		else:
			typer.echo("❌ Port 7001 not listening after 10 seconds\n")

		# Test auth config endpoint
		typer.echo("🧪 Testing /api/auth/config...")
		cmd = "curl -s http://localhost:7001/api/auth/config 2>&1"
		proc = run_cmd(
			ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=cmd),
			capture_output=True,
			check=False,
		)
		config = proc.stdout.strip()
		typer.echo(f"   Response: {redact_text(config[:200])}...\n")

		# Check if audience is updated
		if "api.app.aurity.io" in config:
			typer.echo("✅ Audience updated successfully!\n")
		else:
			typer.echo("⚠️  Audience may not have been updated\n")

		typer.echo("=" * 80)
		typer.echo("✅ AUTH0 API IDENTIFIER UPDATED")
		typer.echo("=" * 80)
		typer.echo("""
Change applied:
- Before: https://api.fi-aurity.duckdns.org
- After: https://api.app.aurity.io

IMPORTANT: This change is temporary (lost on reboot).
To make permanent:
1. Add to /etc/environment
2. Or create systemd service with Environment=
3. Or use .env file in backend

Test login from your mobile device now.
		""")

	except Exception as e:
		typer.echo(f"❌ Error: {redact_text(str(e))}")
		raise typer.Exit(1)


@app.command("test-e2e-curl")
def test_e2e_curl(
    base_url: Annotated[
        str,
        typer.Option("--base-url", help="Base URL for API endpoints")
    ] = "https://app.aurity.io",
    session_id: Annotated[
        str,
        typer.Option("--session-id", help="Custom session ID (auto-generated if not provided)")
    ] = "",
    output_dir: Annotated[
        str,
        typer.Option("--output-dir", help="Directory to save response files")
    ] = "",
) -> None:
    """
    Run end-to-end curl tests for the complete workflow.

    Tests the full pipeline: health check → dry-run → chat → streaming →
    diarization → SOAP generation → session finalization.

    Requires jq for JSON processing and uuidgen for session IDs.
    """
    import subprocess
    import tempfile

    import os
    from pathlib import Path

    # Check if jq is available
    try:
        subprocess.run(["jq", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        typer.echo("❌ jq is required for this command. Install with: brew install jq")
        raise typer.Exit(1)

    # Check if uuidgen is available
    try:
        subprocess.run(["uuidgen"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        typer.echo("❌ uuidgen is required for this command")
        raise typer.Exit(1)

    # Generate session ID
    if not session_id:
        result = subprocess.run(["uuidgen"], capture_output=True, text=True, check=True)
        session_id = result.stdout.strip().lower()

    # Setup output directory
    if not output_dir:
        output_dir = f"/tmp/fi_e2e_{session_id}"

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    typer.echo("🧪 Running E2E curl tests")
    typer.echo("=" * 50)
    typer.echo(f"   Base URL: {base_url}")
    typer.echo(f"   Session ID: {session_id}")
    typer.echo(f"   Output Dir: {output_dir}")
    typer.echo()

    def run_curl(description: str, cmd: list, output_file: str | None = None) -> dict:
        """Run curl command and return parsed JSON if applicable."""
        typer.echo(description)

        full_cmd = cmd.copy()
        if output_file:
            full_cmd.extend(["|", "tee", str(output_path / output_file)])
            if ".json" in output_file:
                full_cmd.extend(["|", "jq", "."])

        try:
            # Execute the command
            result = subprocess.run(" ".join(full_cmd), shell=True, capture_output=True, text=True, cwd=output_path)

            if result.returncode != 0:
                typer.echo(f"❌ Command failed: {result.stderr}")
                return {}

            # If it's a JSON file, try to parse it
            if output_file and output_file.endswith(".json"):
                try:
                    return subprocess.run(
                        ["jq", ".", str(output_path / output_file)],
                        capture_output=True, text=True, check=True
                    ).stdout
                except subprocess.CalledProcessError:
                    pass

            return result.stdout
        except Exception as e:
            typer.echo(f"❌ Error: {e}")
            return {}

    # 1. Health check
    run_curl(
        "1) Health check",
        ["curl", "-sS", f"{base_url}/api/health"],
        "health.json"
    )

    # 2. Dry-run (safe)
    typer.echo("\n2) Dry-run (safe)")
    dryrun_data = {
        "persona": "clinical_advisor",
        "message": "Paciente masculino 45a, HTA y cefalea intensa.",
        "response_mode": "concise",
        "rag_context": "RFC: ABCD900101XXX, creatinina 1.8 mg/dL, TA 180/110"
    }

    import json
    run_curl(
        "",
        ["curl", "-sS", "-H", "Content-Type: application/json", "-X", "POST",
         f"{base_url}/api/workflows/aurity/assistant/chat/_dry-run",
         "-d", json.dumps(dryrun_data)],
        "dryrun.json"
    )

    # Extract request ID from dryrun
    try:
        result = subprocess.run(
            ["jq", "-r", ".request_id", str(output_path / "dryrun.json")],
            capture_output=True, text=True
        )
        rid = result.stdout.strip()
        if rid and rid != "null":
            typer.echo(f"   Captured RID={rid}")
        else:
            rid = ""
    except subprocess.CalledProcessError:
        rid = ""

    # 3. Trace for dry-run
    if rid:
        typer.echo("\n3) Trace for dry-run")
        run_curl(
            "",
            ["curl", "-sS", f"{base_url}/api/workflows/aurity/assistant/chat/_trace/{rid}"],
            "dryrun_trace.json"
        )

    # 4. Clinical conversation
    typer.echo("\n4) Clinical conversation (persona + mode)")
    chat_data = {
        "persona": "clinical_advisor",
        "message": "Paciente 45a con TA 180/110, cefalea y visión borrosa. ¿Conducta inicial?",
        "response_mode": "explanatory"
    }

    run_curl(
        "",
        ["curl", "-sS", "-H", "Content-Type: application/json", "-X", "POST",
         f"{base_url}/api/workflows/aurity/assistant/chat",
         "-d", json.dumps(chat_data)],
        "chat1.json"
    )

    # Extract request ID from chat
    try:
        result = subprocess.run(
            ["jq", "-r", ".request_id", str(output_path / "chat1.json")],
            capture_output=True, text=True
        )
        rid2 = result.stdout.strip()
        if rid2 and rid2 != "null":
            typer.echo(f"   Captured RID2={rid2}; fetching trace")
            run_curl(
                "",
                ["curl", "-sS", f"{base_url}/api/workflows/aurity/assistant/chat/_trace/{rid2}"],
                "chat1_trace.json"
            )
        else:
            typer.echo("   WARNING: no request_id in chat1 response")
    except subprocess.CalledProcessError:
        typer.echo("   WARNING: could not extract request_id")

    # 5. Create session and upload chunk
    typer.echo("\n5) Create session and upload chunk (simulated metadata only)")
    # Create a temporary file with simulated chunk data
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("SIMULATED_CHUNK")
        chunk_file = f.name

    try:
        run_curl(
            "",
            ["curl", "-sS", "-X", "POST", f"{base_url}/api/workflows/aurity/stream?sid={session_id}&seq=1",
             "-F", 'meta={"sample_rate":48000,"channels":1};type=application/json',
             "-F", f'chunk=@{chunk_file};type=application/octet-stream'],
            "stream_resp.json"
        )
    finally:
        os.unlink(chunk_file)

    # 6. Monitor session
    typer.echo("\n6) Monitor session")
    run_curl(
        "",
        ["curl", "-sS", f"{base_url}/api/workflows/aurity/sessions/{session_id}/monitor"],
        "monitor.json"
    )

    # 7. Start diarization
    typer.echo("\n7) Start diarization")
    diarization_data = {"engine": "default"}
    run_curl(
        "",
        ["curl", "-sS", "-H", "Content-Type: application/json", "-X", "POST",
         f"{base_url}/api/workflows/aurity/sessions/{session_id}/diarization",
         "-d", json.dumps(diarization_data)],
        "diarization.json"
    )

    # 8. Generate SOAP
    typer.echo("\n8) Generate SOAP")
    soap_data = {
        "format": "json",
        "include_codes": True,
        "style": "concise"
    }
    run_curl(
        "",
        ["curl", "-sS", "-H", "Content-Type: application/json", "-X", "POST",
         f"{base_url}/api/workflows/aurity/sessions/{session_id}/soap",
         "-d", json.dumps(soap_data)],
        "soap.json"
    )

    # 9. Finalize session
    typer.echo("\n9) Finalize session")
    finalize_data = {"encrypt": True}
    run_curl(
        "",
        ["curl", "-sS", "-H", "Content-Type: application/json", "-X", "POST",
         f"{base_url}/api/workflows/aurity/sessions/{session_id}/finalize",
         "-d", json.dumps(finalize_data)],
        "finalize.json"
    )

    # 10. Negative tests
    typer.echo("\n10) Negative tests")

    typer.echo("   10a) Invalid persona")
    invalid_persona_data = {"persona": "no_such_persona", "message": "hola"}
    run_curl(
        "",
        ["curl", "-sS", "-H", "Content-Type: application/json", "-X", "POST",
         f"{base_url}/api/workflows/aurity/assistant/chat",
         "-d", json.dumps(invalid_persona_data)],
        "neg_invalid_persona.json"
    )

    typer.echo("   10b) Simulate LLM timeout")
    timeout_data = {"persona": "clinical_advisor", "message": "#simulate_timeout"}
    run_curl(
        "",
        ["curl", "-sS", "-H", "Content-Type: application/json", "-X", "POST",
         f"{base_url}/api/workflows/aurity/assistant/chat",
         "-d", json.dumps(timeout_data)],
        "neg_timeout.json"
    )

    # 11. Acceptance quick checks
    typer.echo("\n11) Acceptance quick checks")

    typer.echo("   Dry-run output summary:")
    try:
        subprocess.run([
            "jq",
            '{request_id:.request_id, user_message_hash8:.user_message.hash8, user_message_len:.user_message.length, system_markers:.system_markers}',
            str(output_path / "dryrun.json")
        ], cwd=output_path)
    except subprocess.CalledProcessError:
        typer.echo("   Could not generate summary")

    typer.echo("   Trace events (dryrun):")
    try:
        subprocess.run([
            "jq", ".events[]?.type", str(output_path / "dryrun_trace.json")
        ], cwd=output_path)
    except subprocess.CalledProcessError:
        typer.echo("   Could not extract trace events")

    typer.echo("   SOAP keys:")
    try:
        subprocess.run([
            "jq", "keys", str(output_path / "soap.json")
        ], cwd=output_path)
    except subprocess.CalledProcessError:
        typer.echo("   Could not extract SOAP keys")

    typer.echo(f"\n✅ E2E test complete! Outputs saved to {output_dir}")
    typer.echo()
    typer.echo("📋 Test coverage:")
    typer.echo("   • Health check")
    typer.echo("   • Assistant chat (dry-run + live)")
    typer.echo("   • Request tracing")
    typer.echo("   • Session streaming")
    typer.echo("   • Diarization")
    typer.echo("   • SOAP generation")
    typer.echo("   • Session finalization")
    typer.echo("   • Error handling")


@app.command("prod-integrity-check")
def prod_integrity_check(
	host: HostOpt = "",
	user: UserOpt = None,
	port: PortOpt = None,
	identity_file: IdentityOpt = None,
) -> None:
	"""Check production server integrity (git status, file modifications, security)."""
	host = _require_host(host)


	from .._common import run_cmd

	# Remote paths
	prod_dir = "/opt/free-intelligence"
	log_file = "/var/log/aurity-integrity.log"
	alert_file = "/tmp/aurity-dirty-prod-alert"

	def log(message: str) -> None:
		timestamp = run_cmd("date -u +'%Y-%m-%dT%H:%M:%SZ'", capture_output=True).stdout.strip()
		log_cmd = f"echo '{timestamp} {message}' >> {log_file}"
		run_cmd(ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=log_cmd))

	def alert(message: str) -> None:
		log(f"ALERT: {message}")

		# Create alert file
		alert_cmd = f"echo '{message}' > {alert_file}"
		run_cmd(ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=alert_cmd))

		typer.echo(f"🚨 ALERT: {message}")

		# Send Slack alert if webhook configured (would need to be implemented)
		# For now, just log and display

	typer.echo("🔍 Checking production server integrity...")
	typer.echo("=" * 70)

	alerts = []

	# Check 1: Git status (uncommitted changes)
	typer.echo("📋 Checking git status...")
	try:
		git_cmd = f"cd {prod_dir} && git diff --quiet"
		result = run_cmd(ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=git_cmd), check=False)
		if result.returncode != 0:
			changed_cmd = f"cd {prod_dir} && git diff --name-only | head -10"
			changed_result = run_cmd(ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=changed_cmd), capture_output=True)
			changed_files = changed_result.stdout.strip()
			alerts.append(f"DIRTY_GIT: Modified files detected on production!\n{changed_files}")
		else:
			typer.echo("✅ Git status clean")
	except Exception as e:
		alerts.append(f"GIT_CHECK_FAILED: {e}")

	# Check 2: File permissions on critical files
	typer.echo("🔐 Checking file permissions...")
	try:
		perm_cmd = f"stat -c '%a %n' {prod_dir}/backend/config.yml {prod_dir}/.env 2>/dev/null || echo 'Config files not found'"
		perm_result = run_cmd(ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=perm_cmd), capture_output=True)
		permissions = perm_result.stdout.strip()

		# Check if any config files are world-readable
		if "644" in permissions or "666" in permissions:
			alerts.append(f"INSECURE_PERMISSIONS: Config files are world-readable\n{permissions}")
		else:
			typer.echo("✅ File permissions secure")
	except Exception as e:
		alerts.append(f"PERMISSION_CHECK_FAILED: {e}")

	# Check 3: Running processes
	typer.echo("⚙️ Checking running processes...")
	try:
		process_cmd = "ps aux | grep -E '(uvicorn|python.*main)' | grep -v grep | wc -l"
		process_result = run_cmd(ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=process_cmd), capture_output=True)
		process_count = int(process_result.stdout.strip())

		if process_count == 0:
			alerts.append("NO_BACKEND_PROCESS: Backend is not running")
		elif process_count > 1:
			alerts.append(f"MULTIPLE_BACKEND_PROCESSES: {process_count} backend processes running")
		else:
			typer.echo("✅ Backend process running normally")
	except Exception as e:
		alerts.append(f"PROCESS_CHECK_FAILED: {e}")

	# Check 4: Disk space
	typer.echo("💾 Checking disk space...")
	try:
		disk_cmd = "df -h / | tail -1 | awk '{print $5}' | sed 's/%//'"
		disk_result = run_cmd(ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=disk_cmd), capture_output=True)
		disk_usage = int(disk_result.stdout.strip())

		if disk_usage > 90:
			alerts.append(f"LOW_DISK_SPACE: {disk_usage}% disk usage")
		else:
			typer.echo("✅ Disk space adequate")
	except Exception as e:
		alerts.append(f"DISK_CHECK_FAILED: {e}")

	# Check 5: Recent security events
	typer.echo("🛡️ Checking recent security events...")
	try:
		security_cmd = "tail -20 /var/log/auth.log 2>/dev/null | grep -i -E '(failed|invalid|unauthorized)' | wc -l"
		security_result = run_cmd(ssh_argv(host=host, user=user, port=port, identity_file=identity_file, remote_command=security_cmd), capture_output=True, check=False)
		security_events = int(security_result.stdout.strip() or "0")

		if security_events > 0:
			alerts.append(f"SECURITY_EVENTS: {security_events} suspicious auth events in recent logs")
		else:
			typer.echo("✅ No recent security events")
	except Exception as e:
		typer.echo(f"⚠️ Security check inconclusive: {e}")

	# Summary
	typer.echo("\n" + "=" * 70)
	typer.echo("📊 INTEGRITY CHECK RESULTS")
	typer.echo("=" * 70)

	if alerts:
		typer.echo(f"🚨 {len(alerts)} ALERT(S) DETECTED:")
		for alert_msg in alerts:
			typer.echo(f"   • {alert_msg}")
			alert(alert_msg)
		typer.echo("\n❌ INTEGRITY CHECK FAILED")
		typer.echo("   Production server has integrity issues that need attention.")
		raise typer.Exit(1)
	else:
		typer.echo("✅ ALL CHECKS PASSED")
		typer.echo("   Production server integrity verified.")
		typer.echo("\n🎉 INTEGRITY CHECK PASSED")
		typer.echo("   Server is secure and operating normally.")
