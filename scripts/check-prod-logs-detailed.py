#!/usr/bin/env python3
"""Check production backend logs in detail"""
import paramiko

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)

    # Check if backend is running
    print("🔍 Verificando proceso backend...")
    print("=" * 80)
    stdin, stdout, stderr = client.exec_command("ps aux | grep '[p]ython.*main'")
    process = stdout.read().decode().strip()

    if process:
        print(f"✅ Backend corriendo:\n{process}\n")
    else:
        print("❌ Backend NO está corriendo!\n")

    # Check port
    print("🔍 Verificando puerto 7001...")
    print("=" * 80)
    stdin, stdout, stderr = client.exec_command("ss -tlnp | grep :7001")
    port = stdout.read().decode().strip()

    if port:
        print(f"✅ Puerto 7001 escuchando:\n{port}\n")
    else:
        print("❌ Puerto 7001 NO escuchando!\n")

    # Get last 100 lines of backend logs
    print("📋 ÚLTIMOS 100 LOGS DEL BACKEND:")
    print("=" * 80)
    stdin, stdout, stderr = client.exec_command("tail -n 100 /tmp/backend.log")
    logs = stdout.read().decode()

    if logs:
        print(logs)
    else:
        print("(sin logs recientes)")

    print("\n" + "=" * 80)
    print("🔍 BUSCANDO ERRORES RECIENTES:")
    print("=" * 80)
    stdin, stdout, stderr = client.exec_command("tail -n 200 /tmp/backend.log | grep -i -E '(error|exception|traceback|failed|crash)' | tail -20")
    errors = stdout.read().decode()

    if errors:
        print(errors)
    else:
        print("✅ No se encontraron errores obvios")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    client.close()
