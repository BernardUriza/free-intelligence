#!/usr/bin/env python3
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(
    "104.131.175.65", username="root", password="FreeIntel2024DO!", look_for_keys=False, timeout=30
)

# Check with ss instead of netstat
print("📡 Using ss to check port 80:")
stdin, stdout, stderr = client.exec_command("ss -tlnp | grep :80")
print(stdout.read().decode() or "❌ Nothing")

# Check nginx processes
print("\n🔍 Nginx processes:")
stdin, stdout, stderr = client.exec_command("ps aux | grep nginx")
print(stdout.read().decode())

# Check nginx error log
print("\n📋 Nginx error log (last 30 lines):")
stdin, stdout, stderr = client.exec_command("tail -30 /var/log/nginx/error.log")
print(stdout.read().decode())

# Check if something else is on port 80
print("\n🔍 What is using port 80:")
stdin, stdout, stderr = client.exec_command("lsof -i :80")
print(stdout.read().decode() or "❌ Nothing using port 80")

# Kill nginx and restart fresh
print("\n🔄 Killing all nginx processes and restarting...")
stdin, stdout, stderr = client.exec_command(
    "killall nginx 2>/dev/null ; sleep 2 ; systemctl start nginx ; sleep 2"
)
stdout.channel.recv_exit_status()

print("\n✅ Checking again with ss:")
stdin, stdout, stderr = client.exec_command("ss -tlnp | grep :80")
output = stdout.read().decode()
print(output if output else "❌ Still nothing!")

# One more check - verify nginx is actually running
print("\n✅ Nginx status after restart:")
stdin, stdout, stderr = client.exec_command("systemctl status nginx | head -15")
print(stdout.read().decode())

client.close()
