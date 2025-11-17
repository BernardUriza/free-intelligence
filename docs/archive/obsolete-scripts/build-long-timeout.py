#!/usr/bin/env python3
"""Run build with long timeout and check progress"""
import time

import paramiko

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)
    print("✅ Connected!")

    # Clean previous build
    print("\n🧹 Cleaning previous build...")
    stdin, stdout, stderr = client.exec_command(
        "cd /opt/free-intelligence/apps/aurity && rm -rf .next out"
    )
    stdout.channel.recv_exit_status()

    # Run build without Turbopack and with verbose output
    print("\n🏗️ Starting build (this may take 5-10 minutes)...")
    print("⏱️ Running build in background on server...")

    # Start build in background
    stdin, stdout, stderr = client.exec_command(
        """
        cd /opt/free-intelligence/apps/aurity
        export NODE_ENV=production
        export NEXT_PUBLIC_API_URL=http://104.131.175.65:7001
        nohup pnpm build > /tmp/aurity-build.log 2>&1 &
        echo $!
        """,
        timeout=10,
    )

    pid = stdout.read().decode().strip()
    print(f"📝 Build PID: {pid}")
    print("⏱️ Waiting for build to complete...")

    # Check build status every 30 seconds
    for i in range(20):  # Check for up to 10 minutes
        time.sleep(30)
        print(f"\n⏱️  {(i+1) * 30}s elapsed, checking status...")

        # Check if process still running
        stdin, stdout, stderr = client.exec_command(
            f'ps -p {pid} > /dev/null && echo "running" || echo "finished"'
        )
        status = stdout.read().decode().strip()

        # Show last 20 lines of log
        stdin, stdout, stderr = client.exec_command("tail -20 /tmp/aurity-build.log")
        log = stdout.read().decode()
        print("📋 Build log (last 20 lines):")
        print(log)

        if status == "finished":
            print("\n✅ Build process finished!")
            break

    # Check final status
    print("\n🔍 Checking build output...")
    stdin, stdout, stderr = client.exec_command(
        "ls -lah /opt/free-intelligence/apps/aurity/out/ 2>&1"
    )
    print(stdout.read().decode())

    # Check for index.html
    stdin, stdout, stderr = client.exec_command(
        'find /opt/free-intelligence/apps/aurity/out -name "*.html" 2>&1 | head -10'
    )
    html_files = stdout.read().decode()
    print("\n📄 HTML files generated:")
    print(html_files if html_files else "None found")

    # Show full log if build failed
    if not html_files:
        print("\n❌ No HTML files found. Full build log:")
        stdin, stdout, stderr = client.exec_command("cat /tmp/aurity-build.log")
        print(stdout.read().decode())

finally:
    client.close()
