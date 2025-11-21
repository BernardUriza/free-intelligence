#!/usr/bin/env python3
"""Tail backend logs in real-time"""
import paramiko

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)

    print("📋 LOGS DEL BACKEND (últimas 50 líneas):")
    print("=" * 80)

    # Get last 50 lines
    stdin, stdout, stderr = client.exec_command("tail -n 50 /tmp/backend.log")
    logs = stdout.read().decode()

    print(logs)

    print("\n" + "=" * 80)
    print("🔍 ERRORES Y EXCEPCIONES:")
    print("=" * 80)

    # Get errors
    stdin, stdout, stderr = client.exec_command(
        "tail -n 100 /tmp/backend.log | grep -A 5 -i -E '(error|exception|traceback|failed)' | tail -30"
    )
    errors = stdout.read().decode()

    if errors.strip():
        print(errors)
    else:
        print("✅ No hay errores recientes")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    client.close()
