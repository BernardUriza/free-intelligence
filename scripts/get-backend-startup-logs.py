#!/usr/bin/env python3
"""Get backend startup logs"""
import paramiko

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)

    # Check if process is running
    stdin, stdout, stderr = client.exec_command("ps aux | grep '[u]vicorn'")
    process = stdout.read().decode().strip()

    if process:
        print("✅ Proceso uvicorn corriendo:")
        print(f"   {process}\n")
    else:
        print("❌ Proceso NO corriendo\n")

    # Check port
    stdin, stdout, stderr = client.exec_command("ss -tlnp | grep :7001")
    port = stdout.read().decode().strip()

    if port:
        print(f"✅ Puerto 7001: {port}\n")
    else:
        print("❌ Puerto 7001 NO escuchando\n")

    # Get all backend logs
    print("📋 TODOS los logs del backend:")
    print("=" * 80)
    stdin, stdout, stderr = client.exec_command("cat /tmp/backend.log")
    logs = stdout.read().decode()

    if logs:
        print(logs)
    else:
        print("(vacío)")

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
