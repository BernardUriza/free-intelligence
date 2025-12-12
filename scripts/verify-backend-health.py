#!/usr/bin/env python3
"""Verificar salud del backend"""

import time

import paramiko

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)
    print("✅ Conectado\n")

    # Check process
    stdin, stdout, stderr = client.exec_command("ps aux | grep '[u]vicorn'")
    process = stdout.read().decode().strip()
    if process:
        print("✅ Proceso uvicorn corriendo")
        print(f"   {process}\n")
    else:
        print("❌ Proceso NO encontrado\n")

    # Check port (wait up to 15 seconds)
    print("🔍 Esperando que el puerto 7001 esté disponible...")
    for i in range(15):
        stdin, stdout, stderr = client.exec_command("ss -tlnp | grep :7001")
        port_output = stdout.read().decode().strip()
        if ":7001" in port_output:
            print(f"✅ Puerto 7001 escuchando (después de {i + 1}s)")
            print(f"   {port_output}\n")
            break
        time.sleep(1)
        print(f"   Esperando... ({i + 1}/15)")
    else:
        print("❌ Puerto 7001 NO responde después de 15s\n")
        print("📋 Últimos logs:")
        stdin, stdout, stderr = client.exec_command("tail -n 30 /tmp/backend.log")
        print(stdout.read().decode())

    # Test endpoints
    print("\n🧪 Probando endpoints de la API:")
    endpoints = [
        ("/api/health", "Health Check"),
        ("/api/auth/config", "Auth Config"),
    ]

    for path, name in endpoints:
        stdin, stdout, stderr = client.exec_command(
            f"curl -s -w '\\nSTATUS:%{{http_code}}' -m 3 http://localhost:7001{path} 2>&1"
        )
        response = stdout.read().decode()

        # Parse response
        lines = response.split("\n")
        status_line = [l for l in lines if l.startswith("STATUS:")]
        status = status_line[0].replace("STATUS:", "") if status_line else "TIMEOUT"

        # Get response body (everything before STATUS line)
        body_lines = []
        for line in lines:
            if line.startswith("STATUS:"):
                break
            body_lines.append(line)
        body = "\n".join(body_lines).strip()[:200]  # First 200 chars

        if status == "200":
            print(f"✅ {name} ({path}): HTTP {status}")
            if body:
                print(f"   Response: {body}")
        else:
            print(f"⚠️  {name} ({path}): HTTP {status}")
            if body:
                print(f"   Error: {body}")

    print("\n📊 Estado final:")
    print("=" * 60)
    stdin, stdout, stderr = client.exec_command(
        "echo 'Procesos:' && ps aux | grep '[p]ython.*main' | wc -l && "
        "echo 'Puerto 7001:' && ss -tlnp | grep :7001 | wc -l"
    )
    print(stdout.read().decode())

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
finally:
    client.close()
