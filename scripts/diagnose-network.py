#!/usr/bin/env python3
"""Diagnose network and firewall issues"""
import paramiko

HOST = '104.131.175.65'
USER = 'root'
PASSWORD = 'FreeIntel2024DO!'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)
    print("✅ SSH Connected\n")

    # Check if Nginx is running
    print("1️⃣ Nginx Status:")
    stdin, stdout, stderr = client.exec_command('systemctl status nginx | head -10')
    print(stdout.read().decode())

    # Check what's listening on port 80
    print("\n2️⃣ Port 80 Listeners:")
    stdin, stdout, stderr = client.exec_command('netstat -tlnp | grep :80')
    output = stdout.read().decode()
    print(output if output else "❌ Nothing listening on port 80!")

    # Check firewall status (ufw)
    print("\n3️⃣ UFW Firewall Status:")
    stdin, stdout, stderr = client.exec_command('ufw status verbose')
    print(stdout.read().decode())

    # Check iptables
    print("\n4️⃣ iptables Rules:")
    stdin, stdout, stderr = client.exec_command('iptables -L -n | grep -E "Chain|80"')
    print(stdout.read().decode())

    # Test local curl
    print("\n5️⃣ Local Curl Test:")
    stdin, stdout, stderr = client.exec_command('curl -I http://localhost/ 2>&1 | head -5')
    print(stdout.read().decode())

    # Check Nginx config
    print("\n6️⃣ Nginx Listen Config:")
    stdin, stdout, stderr = client.exec_command('grep -r "listen" /etc/nginx/sites-enabled/')
    print(stdout.read().decode())

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    client.close()
