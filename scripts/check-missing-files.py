#!/usr/bin/env python3
"""Check which files are missing from the server"""
import paramiko

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)
    print("✅ Conectado\n")

    # Get list of CSS files on server
    print("📋 Archivos CSS en el servidor:")
    print("=" * 80)
    stdin, stdout, stderr = client.exec_command(
        "ls -lh /opt/free-intelligence/apps/aurity/out/_next/static/chunks/*.css 2>&1"
    )
    server_css = stdout.read().decode()
    print(server_css if server_css else "❌ No hay archivos CSS\n")

    # Check for specific missing files
    missing_files = [
        "2787eb3c5de6dde5.js",
        "abb749a40dfb2eb5.css"
    ]

    print("\n🔍 Verificando archivos específicos que fallan:")
    print("=" * 80)
    for filename in missing_files:
        stdin, stdout, stderr = client.exec_command(
            f"find /opt/free-intelligence/apps/aurity/out -name '{filename}' 2>&1"
        )
        result = stdout.read().decode().strip()
        if result:
            print(f"✅ {filename}: {result}")
        else:
            print(f"❌ {filename}: NO ENCONTRADO")

    # List all files in chunks directory
    print("\n📂 TODOS los archivos en _next/static/chunks/:")
    print("=" * 80)
    stdin, stdout, stderr = client.exec_command(
        "ls /opt/free-intelligence/apps/aurity/out/_next/static/chunks/ | sort"
    )
    print(stdout.read().decode())

    # Check local build vs server
    print("\n💡 DIAGNÓSTICO:")
    print("=" * 80)
    print("""
El problema es que el HTML está referenciando archivos que NO existen en el servidor.

Posibles causas:
1. El build local generó archivos diferentes a los que se subieron
2. El deployment solo subió algunos archivos (parcial)
3. Hay un problema con Turbopack que genera archivos dinámicamente

Solución:
1. Hacer un build LIMPIO (rm -rf .next .turbo)
2. Verificar que TODOS los archivos se generen
3. Re-desplegar TODOS los archivos
    """)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    client.close()
