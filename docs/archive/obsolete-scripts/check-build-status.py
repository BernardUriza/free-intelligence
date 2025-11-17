#!/usr/bin/env python3
"""Check build status on DigitalOcean"""
import paramiko

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)
    print("✅ Connected!")

    # Check if out/ directory exists
    stdin, stdout, stderr = client.exec_command(
        "ls -lah /opt/free-intelligence/apps/aurity/out/ 2>&1"
    )
    out_check = stdout.read().decode()
    print("\n📁 Build Output Directory:")
    print(out_check[:500])

    # Try to build again
    print("\n🏗️ Running build...")
    stdin, stdout, stderr = client.exec_command(
        "cd /opt/free-intelligence/apps/aurity && timeout 180 pnpm build 2>&1", timeout=200
    )

    # Wait for command
    exit_status = stdout.channel.recv_exit_status()
    output = stdout.read().decode()

    print(output)

    if exit_status == 0:
        print("\n✅ Build completed successfully!")

        # Check output again
        stdin, stdout, stderr = client.exec_command(
            "ls -lah /opt/free-intelligence/apps/aurity/out/"
        )
        print("\n📁 Build output:")
        print(stdout.read().decode())
    else:
        print(f"\n❌ Build failed with exit code {exit_status}")

finally:
    client.close()
