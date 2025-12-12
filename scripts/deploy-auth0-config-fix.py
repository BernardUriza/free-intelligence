#!/usr/bin/env python3
"""Deploy fixed auth0_config.py and restart backend"""

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

    # Stop backend
    print("🛑 Deteniendo backend...")
    stdin, stdout, stderr = client.exec_command("pkill -9 -f 'python.*main'")
    stdout.channel.recv_exit_status()
    time.sleep(2)

    # Upload fixed file
    print("📤 Subiendo auth0_config.py corregido...")
    sftp = client.open_sftp()
    local_path = (
        "/Users/bernardurizaorozco/Documents/free-intelligence/backend/auth/auth0_config.py"
    )
    remote_path = "/opt/free-intelligence/backend/auth/auth0_config.py"
    sftp.put(local_path, remote_path)
    sftp.close()
    print("✅ Archivo actualizado\n")

    # Start backend
    print("🚀 Iniciando backend...")
    start_cmd = """
    cd /opt/free-intelligence && \
    export PYTHONPATH=/opt/free-intelligence:$PYTHONPATH && \
    nohup python3.14 -m backend.app.main > /tmp/backend.log 2>&1 &
    """
    stdin, stdout, stderr = client.exec_command(start_cmd)
    stdout.channel.recv_exit_status()

    # Wait
    print("⏳ Esperando 10 segundos...")
    time.sleep(10)

    # Check process
    stdin, stdout, stderr = client.exec_command("ps aux | grep '[u]vicorn'")
    process = stdout.read().decode().strip()

    if process:
        print("✅ Backend corriendo\n")

        # Test endpoint
        print("🧪 Probando /api/auth/config...")
        stdin, stdout, stderr = client.exec_command(
            "curl -s http://localhost:7001/api/auth/config | python3 -m json.tool | grep audience"
        )
        result = stdout.read().decode()
        print(f"   {result}\n")

        if "api.app.aurity.io" in result:
            print("✅ AUDIENCE ACTUALIZADO!\n")
        else:
            print("⚠️  Audience puede no estar actualizado\n")
    else:
        print("❌ Backend NO arrancó\n")
        print("📋 Últimos logs:")
        stdin, stdout, stderr = client.exec_command("tail -n 40 /tmp/backend.log")
        print(stdout.read().decode())

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
finally:
    client.close()
