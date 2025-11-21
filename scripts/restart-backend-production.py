#!/usr/bin/env python3
"""Reiniciar backend en producción y verificar logs"""
import paramiko
import time
import sys

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)
    print("✅ Conectado\n")

    # Stop old backend process
    print("🛑 Deteniendo backend anterior...")
    stdin, stdout, stderr = client.exec_command("pkill -f 'python.*main.py' || echo 'No process found'")
    stdout.channel.recv_exit_status()
    time.sleep(2)
    print("✅ Proceso detenido\n")

    # Verify it's stopped
    stdin, stdout, stderr = client.exec_command("ps aux | grep '[p]ython.*main.py'")
    if stdout.read().decode().strip():
        print("⚠️  Proceso aún corriendo, matando con -9...")
        stdin, stdout, stderr = client.exec_command("pkill -9 -f 'python.*main.py'")
        stdout.channel.recv_exit_status()
        time.sleep(1)

    # Check current directory structure
    print("📂 Verificando estructura del proyecto...")
    stdin, stdout, stderr = client.exec_command("ls -la /opt/free-intelligence/backend/")
    print(stdout.read().decode())

    # Start backend with proper logging
    print("\n🚀 Iniciando backend...")
    start_cmd = """
    cd /opt/free-intelligence/backend && \
    nohup python3.14 -m app.main > /tmp/backend.log 2>&1 &
    """
    stdin, stdout, stderr = client.exec_command(start_cmd)
    stdout.channel.recv_exit_status()
    time.sleep(3)
    print("✅ Comando de inicio ejecutado\n")

    # Check if it's running
    print("🔍 Verificando que el backend esté corriendo...")
    stdin, stdout, stderr = client.exec_command("ps aux | grep '[p]ython.*main.py'")
    process = stdout.read().decode().strip()

    if process:
        print("✅ Backend corriendo:")
        print(f"   {process}\n")
    else:
        print("❌ Backend NO inició!\n")
        print("📋 Logs de error:")
        stdin, stdout, stderr = client.exec_command("tail -n 30 /tmp/backend.log")
        print(stdout.read().decode())
        client.close()
        sys.exit(1)

    # Check port is listening
    print("🔍 Verificando puerto 7001...")
    stdin, stdout, stderr = client.exec_command("ss -tlnp | grep :7001")
    port_status = stdout.read().decode().strip()

    if port_status:
        print(f"✅ Puerto 7001 escuchando:\n   {port_status}\n")
    else:
        print("❌ Puerto 7001 NO está escuchando!\n")

    # Wait a bit for backend to fully start
    print("⏳ Esperando 3 segundos para que el backend arranque completamente...")
    time.sleep(3)

    # Test API endpoints
    print("\n🧪 Probando endpoints de la API:")
    print("=" * 60)

    test_endpoints = [
        "/api/health",
        "/api/auth/config",
        "/api/workflows/aurity/sessions"
    ]

    for endpoint in test_endpoints:
        stdin, stdout, stderr = client.exec_command(
            f"curl -s -w '\\nHTTP_CODE:%{{http_code}}' http://localhost:7001{endpoint} 2>&1"
        )
        response = stdout.read().decode()
        print(f"\n{endpoint}:")
        print(response[:500])  # Limit output
        print()

    # Show recent logs
    print("\n📋 Últimas 30 líneas de logs del backend:")
    print("=" * 60)
    stdin, stdout, stderr = client.exec_command("tail -n 30 /tmp/backend.log")
    print(stdout.read().decode())

    # Fix image permissions
    print("\n🔧 Arreglando permisos de imágenes...")
    stdin, stdout, stderr = client.exec_command(
        "chmod -R 755 /opt/free-intelligence/apps/aurity/out/images/ 2>/dev/null || echo 'No images dir'"
    )
    print(stdout.read().decode())

    print("\n✅ REINICIO COMPLETADO")
    print("Prueba desde tu celular: https://app.aurity.io/")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    client.close()
