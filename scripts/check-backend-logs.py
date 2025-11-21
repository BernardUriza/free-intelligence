#!/usr/bin/env python3
"""Ver logs del backend en producción"""
import paramiko

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)
    print("✅ Conectado\n")

    # Check if backend is running
    print("🔍 Verificando si el backend está corriendo...")
    stdin, stdout, stderr = client.exec_command("ps aux | grep '[p]ython.*main.py'")
    process = stdout.read().decode().strip()

    if process:
        print("✅ Backend corriendo:")
        print(f"   {process}\n")
    else:
        print("❌ Backend NO está corriendo!\n")

    # Check backend logs (last 50 lines)
    print("📋 Últimas 50 líneas de logs del backend:")
    print("=" * 60)
    stdin, stdout, stderr = client.exec_command(
        "journalctl -u backend -n 50 --no-pager 2>/dev/null || "
        "tail -n 50 /var/log/backend.log 2>/dev/null || "
        "tail -n 50 /opt/free-intelligence/backend/logs/app.log 2>/dev/null || "
        "echo 'No se encontraron logs en ubicaciones estándar'"
    )
    print(stdout.read().decode())

    # Check nginx error logs
    print("\n📋 Últimos errores de Nginx:")
    print("=" * 60)
    stdin, stdout, stderr = client.exec_command("tail -n 20 /var/log/nginx/error.log")
    print(stdout.read().decode())

    # Check if port 7001 is listening
    print("\n🔍 Verificando puerto 7001 (backend):")
    stdin, stdout, stderr = client.exec_command("ss -tlnp | grep :7001 || lsof -i :7001 || echo 'Puerto 7001 NO está en escucha'")
    print(stdout.read().decode())

    # Test backend API from server
    print("\n🧪 Probando API del backend desde el servidor:")
    stdin, stdout, stderr = client.exec_command(
        "curl -s http://localhost:7001/api/health 2>&1 || echo 'Backend no responde'"
    )
    print(stdout.read().decode())

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    client.close()
