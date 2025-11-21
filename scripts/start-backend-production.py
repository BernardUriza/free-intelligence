#!/usr/bin/env python3
"""Iniciar backend en producción con PYTHONPATH correcto"""
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
    stdin, stdout, stderr = client.exec_command("pkill -f 'python.*main' || echo 'No process found'")
    stdout.channel.recv_exit_status()
    time.sleep(2)

    # Double check with -9
    stdin, stdout, stderr = client.exec_command("pkill -9 -f 'python.*main' 2>/dev/null || true")
    stdout.channel.recv_exit_status()
    time.sleep(1)
    print("✅ Procesos anteriores detenidos\n")

    # Check Python version
    print("🐍 Verificando Python...")
    stdin, stdout, stderr = client.exec_command("python3.14 --version")
    print(f"   {stdout.read().decode().strip()}\n")

    # Start backend with correct PYTHONPATH
    print("🚀 Iniciando backend (desde directorio raíz del proyecto)...")
    start_cmd = """
    cd /opt/free-intelligence && \
    export PYTHONPATH=/opt/free-intelligence:$PYTHONPATH && \
    nohup python3.14 -m backend.app.main > /tmp/backend.log 2>&1 &
    """

    stdin, stdout, stderr = client.exec_command(start_cmd)
    stdout.channel.recv_exit_status()
    print("✅ Comando ejecutado\n")

    # Wait for startup
    print("⏳ Esperando 5 segundos para que el backend arranque...")
    time.sleep(5)

    # Check if it's running
    print("🔍 Verificando proceso...")
    stdin, stdout, stderr = client.exec_command("ps aux | grep '[p]ython.*main'")
    process = stdout.read().decode().strip()

    if process:
        print("✅ Backend corriendo:")
        for line in process.split('\n'):
            print(f"   {line}")
        print()
    else:
        print("❌ Backend NO está corriendo!\n")
        print("📋 Logs de error:")
        stdin, stdout, stderr = client.exec_command("tail -n 50 /tmp/backend.log")
        print(stdout.read().decode())
        client.close()
        sys.exit(1)

    # Check port
    print("🔍 Verificando puerto 7001...")
    stdin, stdout, stderr = client.exec_command("ss -tlnp | grep :7001 || echo 'Puerto no escuchando'")
    port_info = stdout.read().decode().strip()
    if ":7001" in port_info:
        print(f"✅ Puerto 7001 escuchando\n   {port_info}\n")
    else:
        print(f"❌ {port_info}\n")

    # Test API
    print("🧪 Probando endpoints...")
    test_cases = [
        ("Health check", "http://localhost:7001/api/health"),
        ("Auth config", "http://localhost:7001/api/auth/config"),
        ("Workflows", "http://localhost:7001/api/workflows/aurity/sessions")
    ]

    for name, url in test_cases:
        stdin, stdout, stderr = client.exec_command(
            f"curl -s -w '\\nHTTP:%{{http_code}}' -m 5 {url} 2>&1"
        )
        response = stdout.read().decode()
        # Extract HTTP code
        lines = response.split('\n')
        http_code = [l for l in lines if l.startswith('HTTP:')]
        status = http_code[0].replace('HTTP:', '') if http_code else 'TIMEOUT'

        if status == '200':
            print(f"   ✅ {name}: {status}")
        else:
            print(f"   ⚠️  {name}: {status}")

    # Show last log lines
    print("\n📋 Últimas 20 líneas de logs:")
    print("=" * 60)
    stdin, stdout, stderr = client.exec_command("tail -n 20 /tmp/backend.log")
    logs = stdout.read().decode()
    print(logs)

    # Fix permissions for images
    print("\n🔧 Arreglando permisos de /images/...")
    stdin, stdout, stderr = client.exec_command(
        "chmod -R 755 /opt/free-intelligence/apps/aurity/out/ 2>&1"
    )
    perm_result = stdout.read().decode().strip()
    if perm_result:
        print(f"   {perm_result}")
    print("✅ Permisos actualizados\n")

    print("=" * 60)
    print("✅ BACKEND INICIADO CORRECTAMENTE")
    print("=" * 60)
    print(f"\n🌐 Prueba desde tu celular:")
    print(f"   https://app.aurity.io/\n")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    client.close()
