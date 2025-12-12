#!/usr/bin/env python3
"""Ver errores recientes del backend y nginx"""

import paramiko

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)
    print("✅ Conectado\n")

    # Get last 30 lines from backend log
    print("=" * 80)
    print("📋 ÚLTIMOS LOGS DEL BACKEND (/tmp/backend.log)")
    print("=" * 80)
    stdin, stdout, stderr = client.exec_command("tail -n 30 /tmp/backend.log")
    print(stdout.read().decode())

    # Get last 30 lines from nginx error log
    print("\n" + "=" * 80)
    print("📋 ÚLTIMOS ERRORES DE NGINX (/var/log/nginx/error.log)")
    print("=" * 80)
    stdin, stdout, stderr = client.exec_command("tail -n 30 /var/log/nginx/error.log")
    print(stdout.read().decode())

    # Get nginx access log (last 20 lines)
    print("\n" + "=" * 80)
    print("📋 ÚLTIMAS PETICIONES (access.log)")
    print("=" * 80)
    stdin, stdout, stderr = client.exec_command(
        "tail -n 20 /var/log/nginx/access.log | grep -E '(api|auth|workflows)' || tail -n 10 /var/log/nginx/access.log"
    )
    print(stdout.read().decode())

    # Check backend process status
    print("\n" + "=" * 80)
    print("📊 ESTADO DEL BACKEND")
    print("=" * 80)
    stdin, stdout, stderr = client.exec_command("ps aux | grep '[u]vicorn' | head -1")
    process = stdout.read().decode().strip()
    if process:
        print(f"✅ Proceso activo:\n   {process}\n")
    else:
        print("❌ Backend NO está corriendo!\n")

    # Check port
    stdin, stdout, stderr = client.exec_command("ss -tlnp | grep :7001")
    port = stdout.read().decode().strip()
    if port:
        print(f"✅ Puerto 7001 escuchando:\n   {port}\n")
    else:
        print("❌ Puerto 7001 NO está escuchando!\n")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
finally:
    client.close()
