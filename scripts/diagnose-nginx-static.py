#!/usr/bin/env python3
"""Diagnosticar problema de archivos estáticos en Nginx"""
import paramiko

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)
    print("✅ Conectado\n")

    # Check if _next directory exists
    print("📂 Verificando estructura de archivos:")
    print("=" * 80)
    stdin, stdout, stderr = client.exec_command(
        "ls -la /opt/free-intelligence/apps/aurity/out/ | head -20"
    )
    print(stdout.read().decode())

    # Check _next/static/chunks
    print("\n📂 Verificando _next/static/chunks:")
    print("=" * 80)
    stdin, stdout, stderr = client.exec_command(
        "ls -la /opt/free-intelligence/apps/aurity/out/_next/static/chunks/ 2>&1 | head -20"
    )
    output = stdout.read().decode()
    print(output)

    # Check specific file that's failing
    print("\n🔍 Buscando archivo específico (2787eb3c5de6dde5.js):")
    print("=" * 80)
    stdin, stdout, stderr = client.exec_command(
        "find /opt/free-intelligence/apps/aurity/out -name '2787eb3c5de6dde5.js' 2>&1"
    )
    file_location = stdout.read().decode().strip()
    if file_location:
        print(f"✅ Encontrado: {file_location}")
        # Check file type
        stdin, stdout, stderr = client.exec_command(f"file {file_location}")
        print(f"   Tipo: {stdout.read().decode().strip()}")
    else:
        print("❌ Archivo NO encontrado en el servidor!")

    # Check Nginx config
    print("\n📋 Configuración de Nginx:")
    print("=" * 80)
    stdin, stdout, stderr = client.exec_command("cat /etc/nginx/sites-enabled/aurity")
    print(stdout.read().decode())

    # Test actual HTTP response
    print("\n🧪 Test HTTP de archivo estático:")
    print("=" * 80)
    stdin, stdout, stderr = client.exec_command(
        "curl -I http://localhost/_next/static/chunks/2787eb3c5de6dde5.js 2>&1 | head -15"
    )
    print(stdout.read().decode())

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    client.close()
