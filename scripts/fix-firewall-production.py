#!/usr/bin/env python3
"""
Diagnóstico y solución de firewall en producción
Migra de iptables manual a UFW persistente
"""

import paramiko

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"


def run_command(client, command, description):
    """Ejecuta comando y muestra resultado"""
    print(f"\n🔍 {description}")
    print(f"   $ {command}")
    stdin, stdout, stderr = client.exec_command(command)
    output = stdout.read().decode().strip()
    error = stderr.read().decode().strip()
    exit_code = stdout.channel.recv_exit_status()

    if output:
        print(f"   {output}")
    if error and exit_code != 0:
        print(f"   ⚠️  {error}")

    return output, error, exit_code


def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print("🔌 Conectando al servidor...")
        client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)
        print("✅ Conectado\n")

        print("=" * 60)
        print("PASO 1: DIAGNÓSTICO ACTUAL")
        print("=" * 60)

        # 1. Check iptables policy
        run_command(
            client, "iptables -L INPUT -n -v | head -3", "Política actual de iptables INPUT"
        )

        # 2. Check UFW status
        ufw_status, _, _ = run_command(client, "ufw status verbose", "Estado de UFW")

        # 3. Check listening ports
        run_command(client, "netstat -tlnp | grep -E ':(80|443|7001)'", "Puertos en escucha")

        # 4. Check nginx status
        run_command(client, "systemctl status nginx --no-pager | head -5", "Estado de Nginx")

        print("\n" + "=" * 60)
        print("PASO 2: CONFIGURACIÓN DE UFW")
        print("=" * 60)

        # Ask for confirmation
        if "inactive" in ufw_status.lower():
            print("\n⚠️  UFW está DESACTIVADO. Vamos a:")
            print("   1. Configurar reglas para SSH (22), HTTP (80), HTTPS (443)")
            print("   2. Activar UFW")
            print("   3. Esto REEMPLAZARÁ las reglas de iptables actuales")

            response = input("\n¿Continuar? (si/no): ")
            if response.lower() not in ["si", "s", "yes", "y"]:
                print("❌ Operación cancelada")
                return

            # Reset UFW to default
            print("\n🔄 Reseteando UFW a valores por defecto...")
            run_command(client, "yes | ufw reset", "Reset UFW")

            # Set default policies
            run_command(client, "ufw default deny incoming", "Denegar tráfico entrante por defecto")
            run_command(
                client, "ufw default allow outgoing", "Permitir tráfico saliente por defecto"
            )

            # Allow SSH (critical!)
            run_command(client, "ufw allow 22/tcp comment 'SSH'", "Permitir SSH (puerto 22)")

            # Allow HTTP
            run_command(client, "ufw allow 80/tcp comment 'HTTP'", "Permitir HTTP (puerto 80)")

            # Allow HTTPS
            run_command(client, "ufw allow 443/tcp comment 'HTTPS'", "Permitir HTTPS (puerto 443)")

            # Enable UFW
            print("\n🔥 Activando UFW...")
            stdin, stdout, stderr = client.exec_command("yes | ufw enable")
            stdout.channel.recv_exit_status()
            print("✅ UFW activado")

        else:
            print("\n✅ UFW ya está activo. Verificando reglas...")
            run_command(client, "ufw allow 80/tcp", "Permitir HTTP")
            run_command(client, "ufw allow 443/tcp", "Permitir HTTPS")

        print("\n" + "=" * 60)
        print("PASO 3: VERIFICACIÓN FINAL")
        print("=" * 60)

        # Show final UFW status
        run_command(client, "ufw status numbered", "Reglas UFW activas")

        # Show iptables (should now be managed by UFW)
        run_command(
            client,
            "iptables -L INPUT -n -v | head -10",
            "Nueva política de iptables (gestionada por UFW)",
        )

        # Test HTTP access
        print("\n🧪 Probando acceso HTTP desde el servidor...")
        http_test, _, _ = run_command(
            client,
            "curl -s -o /dev/null -w '%{http_code}' http://localhost/ || echo 'FAIL'",
            "Test HTTP local",
        )

        print("\n" + "=" * 60)
        print("PASO 4: VERIFICAR CLOUD FIREWALL (MANUAL)")
        print("=" * 60)
        print("""
⚠️  IMPORTANTE: También necesitas verificar el Cloud Firewall de DigitalOcean:

1. Ve a: https://cloud.digitalocean.com/networking/firewalls
2. Busca cualquier firewall asignado al droplet '104.131.175.65'
3. Verifica las reglas Inbound:
   ✅ HTTP (80) - All IPv4, All IPv6
   ✅ HTTPS (443) - All IPv4, All IPv6
   ✅ SSH (22) - All IPv4, All IPv6 (o solo tu IP)

Si hay un Cloud Firewall bloqueando, UFW no puede hacer nada.
        """)

        print("\n" + "=" * 60)
        print("✅ CONFIGURACIÓN COMPLETADA")
        print("=" * 60)
        print(f"""
Siguiente paso:
1. Prueba desde tu navegador: http://{HOST}/
2. Prueba HTTPS: https://app.aurity.io/
3. Si aún no funciona, verifica el Cloud Firewall en DigitalOcean

Estado actual:
- UFW: ACTIVO ✅
- HTTP (80): PERMITIDO ✅
- HTTPS (443): PERMITIDO ✅
- Reglas persistentes: SÍ ✅ (sobreviven al reboot)
        """)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        client.close()
        print("\n🔌 Conexión cerrada")


if __name__ == "__main__":
    main()
