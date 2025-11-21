#!/usr/bin/env python3
"""Deploy backend fix for HDF5 path and restart"""
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

    # Stop backend
    print("🛑 Deteniendo backend...")
    stdin, stdout, stderr = client.exec_command("pkill -9 -f 'python.*main' || echo 'No process'")
    stdout.channel.recv_exit_status()
    time.sleep(2)
    print("✅ Backend detenido\n")

    # Clear any HDF5 lock files
    print("🔓 Liberando locks de HDF5...")
    stdin, stdout, stderr = client.exec_command(
        "find /opt/free-intelligence/storage -name '*.h5.lock' -delete 2>/dev/null || true"
    )
    stdout.channel.recv_exit_status()
    print("✅ Locks liberados\n")

    # Deploy updated file
    print("📤 Desplegando archivo actualizado...")
    sftp = client.open_sftp()

    try:
        # Upload finalize.py
        local_path = "/Users/bernardurizaorozco/Documents/free-intelligence/backend/api/internal/sessions/finalize.py"
        remote_path = "/opt/free-intelligence/backend/api/internal/sessions/finalize.py"

        sftp.put(local_path, remote_path)
        print(f"✅ Archivo desplegado: finalize.py\n")

    finally:
        sftp.close()

    # Verify corpus.h5 exists in production
    print("🔍 Verificando corpus.h5 en producción...")
    stdin, stdout, stderr = client.exec_command("ls -lh /opt/free-intelligence/storage/corpus.h5")
    corpus_info = stdout.read().decode().strip()
    if corpus_info:
        print(f"✅ Archivo HDF5 encontrado:\n   {corpus_info}\n")
    else:
        print("⚠️  corpus.h5 NO encontrado en producción!\n")

    # Start backend
    print("🚀 Iniciando backend...")
    start_cmd = """
    cd /opt/free-intelligence && \
    export PYTHONPATH=/opt/free-intelligence:$PYTHONPATH && \
    nohup python3.14 -m backend.app.main > /tmp/backend.log 2>&1 &
    """
    stdin, stdout, stderr = client.exec_command(start_cmd)
    stdout.channel.recv_exit_status()
    print("✅ Comando ejecutado\n")

    # Wait for startup
    print("⏳ Esperando 8 segundos para que arranque...")
    time.sleep(8)

    # Verify process
    stdin, stdout, stderr = client.exec_command("ps aux | grep '[u]vicorn'")
    process = stdout.read().decode().strip()

    if process:
        print("✅ Backend corriendo:")
        print(f"   {process}\n")
    else:
        print("❌ Backend NO está corriendo!\n")
        print("📋 Últimos 40 líneas de logs:")
        stdin, stdout, stderr = client.exec_command("tail -n 40 /tmp/backend.log")
        print(stdout.read().decode())
        client.close()
        exit(1)

    # Verify port
    print("🔍 Verificando puerto 7001...")
    for i in range(10):
        stdin, stdout, stderr = client.exec_command("ss -tlnp | grep :7001")
        port = stdout.read().decode().strip()
        if ":7001" in port:
            print(f"✅ Puerto 7001 escuchando (después de {i+1}s)\n")
            break
        time.sleep(1)
    else:
        print("❌ Puerto 7001 NO responde\n")

    # Test API
    print("🧪 Probando API...")
    stdin, stdout, stderr = client.exec_command(
        "curl -s -w '\\nHTTP:%{http_code}' http://localhost:7001/api/auth/config 2>&1"
    )
    response = stdout.read().decode()
    if "HTTP:200" in response:
        print("✅ API respondiendo correctamente!\n")
        # Show first line of response
        first_line = response.split('\n')[0][:100]
        print(f"   Response: {first_line}...\n")
    else:
        print(f"⚠️  API response:\n{response}\n")

    # Show last logs
    print("📋 Últimas 15 líneas de logs:")
    print("=" * 80)
    stdin, stdout, stderr = client.exec_command("tail -n 15 /tmp/backend.log")
    print(stdout.read().decode())

    print("\n" + "=" * 80)
    print("✅ DEPLOYMENT COMPLETADO")
    print("=" * 80)
    print("\n🌐 Prueba desde tu celular: https://app.aurity.io/\n")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    client.close()
