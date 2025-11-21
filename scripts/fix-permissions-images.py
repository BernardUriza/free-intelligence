#!/usr/bin/env python3
"""Fix permissions for images and static files"""
import paramiko

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)
    print("✅ Conectado\n")

    # Fix all permissions recursively
    print("🔧 Arreglando permisos de archivos estáticos...")
    stdin, stdout, stderr = client.exec_command(
        "chmod -R 755 /opt/free-intelligence/apps/aurity/out/"
    )
    stdout.channel.recv_exit_status()
    print("✅ Permisos actualizados\n")

    # Verify fi.png specifically
    print("🔍 Verificando fi.png:")
    stdin, stdout, stderr = client.exec_command(
        "ls -lh /opt/free-intelligence/apps/aurity/out/images/fi.png"
    )
    print(stdout.read().decode())

    # Test access
    print("\n🧪 Probando acceso a imagen:")
    stdin, stdout, stderr = client.exec_command(
        "curl -I http://localhost/images/fi.png 2>&1 | grep HTTP"
    )
    print(stdout.read().decode())

    print("✅ Permisos corregidos")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    client.close()
