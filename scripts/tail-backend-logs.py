#!/usr/bin/env python3
"""Monitor de logs del backend en tiempo real"""
import paramiko
import sys

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("🔌 Conectando al servidor...")
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)
    print("✅ Conectado\n")
    print("=" * 80)
    print("📋 LOGS EN TIEMPO REAL - Presiona Ctrl+C para detener")
    print("=" * 80)
    print()

    # Tail both backend and nginx logs
    cmd = """
    tail -n 0 -f /tmp/backend.log 2>&1 &
    BACKEND_PID=$!
    tail -n 0 -f /var/log/nginx/error.log 2>&1 &
    NGINX_PID=$!
    trap "kill $BACKEND_PID $NGINX_PID 2>/dev/null" EXIT
    wait
    """

    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)

    print("🟢 Esperando peticiones... (prueba desde tu celular ahora)\n")

    # Read output in real-time
    while True:
        line = stdout.readline()
        if not line:
            break
        # Highlight errors and warnings
        line_lower = line.lower()
        if 'error' in line_lower or 'exception' in line_lower:
            print(f"🔴 {line.rstrip()}")
        elif 'warning' in line_lower or 'warn' in line_lower:
            print(f"🟡 {line.rstrip()}")
        elif 'http' in line_lower or 'request' in line_lower:
            print(f"🔵 {line.rstrip()}")
        else:
            print(f"   {line.rstrip()}")

except KeyboardInterrupt:
    print("\n\n⏸️  Monitoreo detenido por el usuario")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    client.close()
    print("\n🔌 Conexión cerrada")
