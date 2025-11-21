#!/usr/bin/env python3
"""Fix Auth0 API Identifier mismatch"""
import paramiko
import time

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)
    print("✅ Conectado\n")

    # Check current environment
    print("🔍 Verificando variable actual:")
    print("=" * 80)
    stdin, stdout, stderr = client.exec_command("printenv | grep AUTH0_API_IDENTIFIER || echo 'Not set'")
    current = stdout.read().decode().strip()
    print(f"   Actual: {current}\n")

    # Update backend startup script or environment
    print("📝 Actualizando AUTH0_API_IDENTIFIER...")

    # Option 1: Set in systemd service file (if exists)
    # Option 2: Set in shell profile
    # Option 3: Set inline in startup command

    # For quick fix, we'll update the startup command
    # First, stop backend
    print("🛑 Deteniendo backend...")
    stdin, stdout, stderr = client.exec_command("pkill -9 -f 'python.*main'")
    stdout.channel.recv_exit_status()
    time.sleep(2)
    print("✅ Backend detenido\n")

    # Start with updated environment variable
    print("🚀 Iniciando backend con nueva configuración...")
    start_cmd = """
    cd /opt/free-intelligence && \
    export PYTHONPATH=/opt/free-intelligence:$PYTHONPATH && \
    export AUTH0_API_IDENTIFIER=https://api.app.aurity.io && \
    nohup python3.14 -m backend.app.main > /tmp/backend.log 2>&1 &
    """

    stdin, stdout, stderr = client.exec_command(start_cmd)
    stdout.channel.recv_exit_status()
    print("✅ Comando ejecutado\n")

    # Wait for startup
    print("⏳ Esperando 8 segundos...")
    time.sleep(8)

    # Verify process
    print("🔍 Verificando proceso...")
    stdin, stdout, stderr = client.exec_command("ps aux | grep '[u]vicorn'")
    process = stdout.read().decode().strip()

    if process:
        print(f"✅ Backend corriendo:\n   {process}\n")
    else:
        print("❌ Backend NO está corriendo!\n")
        print("📋 Logs:")
        stdin, stdout, stderr = client.exec_command("tail -n 30 /tmp/backend.log")
        print(stdout.read().decode())
        client.close()
        exit(1)

    # Verify port
    print("🔍 Verificando puerto 7001...")
    for i in range(10):
        stdin, stdout, stderr = client.exec_command("ss -tlnp | grep :7001")
        if stdout.read().decode().strip():
            print(f"✅ Puerto 7001 escuchando (después de {i+1}s)\n")
            break
        time.sleep(1)

    # Test auth config endpoint
    print("🧪 Probando /api/auth/config...")
    stdin, stdout, stderr = client.exec_command(
        "curl -s http://localhost:7001/api/auth/config 2>&1"
    )
    config = stdout.read().decode()
    print(f"   Response: {config[:200]}...\n")

    # Check if audience is updated
    if "api.app.aurity.io" in config:
        print("✅ Audience actualizado correctamente!\n")
    else:
        print("⚠️  Audience puede no haberse actualizado\n")

    print("=" * 80)
    print("✅ AUTH0 API IDENTIFIER ACTUALIZADO")
    print("=" * 80)
    print("""
Cambio aplicado:
- Antes: https://api.fi-aurity.duckdns.org
- Ahora: https://api.app.aurity.io

IMPORTANTE: Este cambio es temporal (se pierde en reboot).
Para hacerlo permanente:
1. Agregar a /etc/environment
2. O crear systemd service con Environment=
3. O usar .env file en el backend

Prueba el login desde tu celular ahora.
    """)

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    client.close()
