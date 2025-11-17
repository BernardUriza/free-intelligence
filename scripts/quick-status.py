#!/usr/bin/env python3
import paramiko

HOST = '104.131.175.65'
USER = 'root'
PASSWORD = 'FreeIntel2024DO!'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)

# Check build log
stdin, stdout, stderr = client.exec_command('tail -50 /tmp/aurity-build.log 2>&1')
print("📋 Build Log (last 50 lines):")
print(stdout.read().decode())

# Check if build process is running
stdin, stdout, stderr = client.exec_command('ps aux | grep -E "(pnpm|next) build" | grep -v grep')
print("\n🔍 Build processes:")
print(stdout.read().decode() or "No build process running")

# Check output directory
stdin, stdout, stderr = client.exec_command('find /opt/free-intelligence/apps/aurity/out -name "*.html" 2>/dev/null | head -5')
html = stdout.read().decode()
print("\n📄 HTML files:")
print(html if html else "None yet")

client.close()
