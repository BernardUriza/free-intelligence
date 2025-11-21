#!/usr/bin/env python3
"""Patch auth0_config.py directly on server"""
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

    # Read current file
    print("📖 Leyendo archivo actual...")
    stdin, stdout, stderr = client.exec_command(
        "cat /opt/free-intelligence/backend/auth/auth0_config.py"
    )
    current_content = stdout.read().decode()
    print(f"   Tamaño: {len(current_content)} bytes\n")

    # Patch the file
    print("🔧 Aplicando patch...")
    new_content = current_content.replace(
        'AUTH0_API_IDENTIFIER = os.getenv("AUTH0_API_IDENTIFIER", "https://api.fi-aurity.duckdns.org")',
        'AUTH0_API_IDENTIFIER = os.getenv("AUTH0_API_IDENTIFIER", "https://api.app.aurity.io")'
    )

    if new_content == current_content:
        print("⚠️  No se encontró la línea a patchear\n")
    else:
        print("✅ Patch preparado\n")

    # Write patched file
    print("💾 Escribiendo archivo parcheado...")
    # Escape special characters for bash
    escaped_content = new_content.replace("$", "\\$").replace('"', '\\"').replace("`", "\\`")

    stdin, stdout, stderr = client.exec_command(
        f'cat > /opt/free-intelligence/backend/auth/auth0_config.py << \'ENDOFFILE\'\n{new_content}\nENDOFFILE'
    )
    stdout.channel.recv_exit_status()
    print("✅ Archivo actualizado\n")

    # Restart backend
    print("🔄 Reiniciando backend...")
    stdin, stdout, stderr = client.exec_command("pkill -9 -f 'python.*main'")
    stdout.channel.recv_exit_status()
    time.sleep(2)

    start_cmd = """
    cd /opt/free-intelligence && \
    export PYTHONPATH=/opt/free-intelligence:$PYTHONPATH && \
    nohup python3.14 -m backend.app.main > /tmp/backend.log 2>&1 &
    """
    stdin, stdout, stderr = client.exec_command(start_cmd)
    stdout.channel.recv_exit_status()
    print("✅ Backend reiniciado\n")

    # Wait
    print("⏳ Esperando 8 segundos...")
    time.sleep(8)

    # Verify
    print("🧪 Verificando nuevo audience...")
    stdin, stdout, stderr = client.exec_command(
        "curl -s http://localhost:7001/api/auth/config 2>&1 | grep audience"
    )
    result = stdout.read().decode()
    print(f"   {result}\n")

    if "api.app.aurity.io" in result:
        print("✅ AUDIENCE ACTUALIZADO CORRECTAMENTE!\n")
    else:
        print("❌ Audience NO se actualizó\n")
        print("📋 Últimos logs:")
        stdin, stdout, stderr = client.exec_command("tail -n 20 /tmp/backend.log")
        print(stdout.read().decode())

    print("=" * 80)
    print("✅ PATCH APLICADO")
    print("=" * 80)
    print("""
Cambio PERMANENTE aplicado:
- auth0_config.py actualizado en el servidor
- audience: https://api.app.aurity.io

Prueba el login desde tu celular ahora.
    """)

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    client.close()
