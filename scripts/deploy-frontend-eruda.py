#!/usr/bin/env python3
"""Deploy frontend with Eruda to production"""
import paramiko
import os

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"
LOCAL_OUT = "/Users/bernardurizaorozco/Documents/free-intelligence/apps/aurity/out"
REMOTE_OUT = "/opt/free-intelligence/apps/aurity/out"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)
    print("✅ Conectado\n")

    # Create backup
    print("💾 Creando backup del frontend actual...")
    stdin, stdout, stderr = client.exec_command(
        f"cp -r {REMOTE_OUT} {REMOTE_OUT}.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true"
    )
    stdout.channel.recv_exit_status()
    print("✅ Backup creado\n")

    # Remove old files
    print("🗑️  Limpiando archivos antiguos...")
    stdin, stdout, stderr = client.exec_command(f"rm -rf {REMOTE_OUT}/*")
    stdout.channel.recv_exit_status()
    print("✅ Archivos eliminados\n")

    # Upload new files via SCP
    print("📤 Subiendo nuevos archivos...")
    sftp = client.open_sftp()

    def upload_directory(local_dir, remote_dir):
        """Recursively upload directory"""
        try:
            sftp.stat(remote_dir)
        except FileNotFoundError:
            sftp.mkdir(remote_dir)

        for item in os.listdir(local_dir):
            local_path = os.path.join(local_dir, item)
            remote_path = f"{remote_dir}/{item}"

            if os.path.isfile(local_path):
                print(f"   Uploading: {item}")
                sftp.put(local_path, remote_path)
            elif os.path.isdir(local_path):
                upload_directory(local_path, remote_path)

    upload_directory(LOCAL_OUT, REMOTE_OUT)
    sftp.close()
    print("\n✅ Archivos subidos\n")

    # Fix permissions
    print("🔧 Arreglando permisos...")
    stdin, stdout, stderr = client.exec_command(f"chmod -R 755 {REMOTE_OUT}")
    stdout.channel.recv_exit_status()
    print("✅ Permisos actualizados\n")

    # Reload Nginx
    print("🔄 Recargando Nginx...")
    stdin, stdout, stderr = client.exec_command("nginx -t && nginx -s reload")
    test_output = stderr.read().decode()
    if "successful" in test_output:
        print("✅ Nginx recargado\n")
    else:
        print(f"⚠️  Nginx test output:\n{test_output}\n")

    print("=" * 80)
    print("✅ DEPLOYMENT COMPLETADO")
    print("=" * 80)
    print("\n🌐 Prueba desde tu celular: https://app.aurity.io/")
    print("📱 Verás un ícono flotante en la esquina inferior derecha")
    print("🔍 Toca el ícono para abrir la consola de Eruda")
    print("\n⚠️  RECUERDA: Remover Eruda después de debugging\n")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    client.close()
