#!/usr/bin/env python3
"""Check Next.js config and build output"""
import paramiko

HOST = '104.131.175.65'
USER = 'root'
PASSWORD = 'FreeIntel2024DO!'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)
    print("✅ Connected!")

    # Check which config is active
    print("\n📝 Current next.config.js:")
    stdin, stdout, stderr = client.exec_command('head -20 /opt/free-intelligence/apps/aurity/next.config.js')
    print(stdout.read().decode())

    # Check if .next exists and what's in it
    print("\n📁 .next directory:")
    stdin, stdout, stderr = client.exec_command('ls -lah /opt/free-intelligence/apps/aurity/.next/ 2>&1 | head -20')
    print(stdout.read().decode())

    # Check if there's a standalone build
    print("\n📁 .next/standalone:")
    stdin, stdout, stderr = client.exec_command('ls -lah /opt/free-intelligence/apps/aurity/.next/standalone/ 2>&1 | head -10')
    print(stdout.read().decode())

    # Check out directory in detail
    print("\n📁 out directory detailed:")
    stdin, stdout, stderr = client.exec_command('find /opt/free-intelligence/apps/aurity/out -type f 2>&1 | head -20')
    print(stdout.read().decode())

    # Check if there's an index.html anywhere
    print("\n🔍 Looking for index.html:")
    stdin, stdout, stderr = client.exec_command('find /opt/free-intelligence/apps/aurity -name "index.html" 2>&1')
    print(stdout.read().decode())

finally:
    client.close()
